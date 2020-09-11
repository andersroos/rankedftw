import gzip
import os
import json
import shutil
import tempfile

from django.db import IntegrityError

import aid.test.init_django_sqlite

from aid.test.base import DjangoTestCase
from common.utils import utcnow
from main.archive import DataArchiver
from main.models import Season, Region, Cache, Ranking


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.db.create_season()
        self.s27 = self.db.create_season(id=27)
        self.s28 = self.db.create_season(id=28)
    
    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Season])
        self.now = utcnow()
        self.tmp_dir = tempfile.mkdtemp(prefix='test_tmp_%s' % self.id())
        self.archiver = DataArchiver(self.now, dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        super().tearDown()

    def test_archive_ranking(self):
        r = self.db.create_ranking(
            data_time=self.datetime(days=-101),
            status=Ranking.COMPLETE_WITH_DATA,
        )

        c1 = self.db.create_cache(
            region=Region.EU,
            bid=1,
            type=Cache.LADDER,
            url="123",
            status=200,
            created=self.datetime(days=-20),
            updated=self.datetime(days=-10),
            data={'arne': 'sune'},
            ranking=r,
        )

        c2 = self.db.create_cache(
            region=Region.AM,
            bid=2,
            type=Cache.LADDER,
            url="456",
            status=404,
            created=self.datetime(days=-200),
            updated=self.datetime(days=-100),
            data={'kuno': 'bertil'},
            ranking=r,
        )

        self.archiver.archive_rankings()

        filename = "%s/archive-ranking-%d.gz" % (self.tmp_dir, r.id)

        r.refresh_from_db()

        self.assertTrue(os.path.exists(filename))
        self.assertEqual(Ranking.COMPLETE_WITOUT_DATA, r.status)
        self.assertRaises(Cache.DoesNotExist, self.db.get, Cache, id=c1.id)
        self.assertRaises(Cache.DoesNotExist, self.db.get, Cache, id=c2.id)

        self.archiver.load_ranking_archive(filename)

        c1 = self.db.get(Cache, id=c1.id)
        self.assertEqual(Region.EU, c1.region)
        self.assertEqual(1, c1.bid)
        self.assertEqual(Cache.LADDER, c1.type)
        self.assertEqual("123", c1.url)
        self.assertEqual(200, c1.status)
        self.assertEqual(self.datetime(days=-20), c1.created)
        self.assertEqual(self.datetime(days=-10), c1.updated)
        self.assertEqual({'arne': 'sune'}, json.loads(c1.data))
        self.assertEqual(r.id, c1.ranking_id)
        self.assertEqual(None, c1.ladder_id)

        c2 = self.db.get(Cache, id=c2.id)
        self.assertEqual(Region.AM, c2.region)
        self.assertEqual(2, c2.bid)
        self.assertEqual(Cache.LADDER, c2.type)
        self.assertEqual("456", c2.url)
        self.assertEqual(404, c2.status)
        self.assertEqual(self.datetime(days=-200), c2.created)
        self.assertEqual(self.datetime(days=-100), c2.updated)
        self.assertEqual({'kuno': 'bertil'}, json.loads(c2.data))
        self.assertEqual(r.id, c2.ranking_id)
        self.assertEqual(None, c2.ladder_id)

    def test_archive_does_not_archive_too_new(self):
        r = self.db.create_ranking(
            data_time=self.datetime(days=-99),
            status=Ranking.COMPLETE_WITH_DATA,
        )

        c1 = self.db.create_cache(ranking=r)
        
        self.archiver.archive_rankings()

        self.db.get(Cache, id=c1.id)

    def test_archive_does_not_archive_bad_state(self):
        r = self.db.create_ranking(
            data_time=self.datetime(days=-99),
            status=Ranking.COMPLETE_WITOUT_DATA,
        )

        c1 = self.db.create_cache(ranking=r)

        self.archiver.archive_rankings()

        self.db.get(Cache, id=c1.id)

    def test_archive_unused_archives_data(self):
        l27 = self.db.create_ladder(season=self.s27)
        c1 = self.db.create_cache(ladder=l27, type=Cache.LADDER)
        c2 = self.db.create_cache(type=Cache.PLAYER_LADDERS)
        c3 = self.db.create_cache(ladder=None, ranking=None)
    
        filename = self.archiver.archive_unused_caches()

        for c in (c1, c2, c3):
            with self.assertRaises(Cache.DoesNotExist): self.db.get(Cache, id=c.id)
            with self.assertRaises(Cache.DoesNotExist): self.db.get(Cache, bid=c.bid, type=c.type, region=c.region)
    
        self.archiver.load_unused_cache_archive(filename)

        for c in (c1, c2, c3):
            self.db.get(Cache, id=c.id)
            self.db.get(Cache, bid=c.bid, type=c.type, region=c.region)

    def test_archive_unused_load_does_not_overwrite_data(self):
        c = self.db.create_cache(type=Cache.PLAYER_LADDERS)

        filename = self.archiver.archive_unused_caches()

        with self.assertRaises(Cache.DoesNotExist): self.db.get(Cache, id=c.id)
        with self.assertRaises(Cache.DoesNotExist): self.db.get(Cache, bid=c.bid, type=c.type, region=c.region)
    
        self.archiver.load_unused_cache_archive(filename)

        c.status = 123
        c.save()

        with self.assertRaises(IntegrityError):
            self.archiver.load_unused_cache_archive(filename)
            
        c.refresh_from_db()
        self.assertEqual(123, c.status)

    def test_archive_unused_load_does_not_archive_and_remove_used_data(self):
        r = self.db.create_ranking()
        l28 = self.db.create_ladder(season=self.s28)
        
        caches = (
            self.db.create_cache(type=Cache.PLAYER),                            # Players kept.
            self.db.create_cache(type=Cache.SEASON),                            # Seasons kept.
            self.db.create_cache(type=Cache.LEAGUE),                            # Leagues kept.
            self.db.create_cache(type=Cache.LADDER, ladder=l28, ranking=None),  # Referenced ladder 28 kept.
            self.db.create_cache(type=Cache.LADDER, ladder=None, ranking=r),    # With referenced ranking kept.
        )

        self.archiver.archive_unused_caches()
        
        for c in caches:
            self.db.get(Cache, id=c.id)
            self.db.get(Cache, bid=c.bid, type=c.type, region=c.region)

    def test_archive_load_save_none_data(self):
        c = self.db.create_cache(ladder=None, ranking=None, data=None)
        filename = self.archiver.archive_unused_caches()
        self.archiver.load_unused_cache_archive(filename)
        c = self.db.get(Cache, id=c.id)
        self.assertEqual(None, c.data)
        
    

    
