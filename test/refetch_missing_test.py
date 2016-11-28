from unittest.mock import Mock

import aid.test.init_django_sqlite

from aid.test.base import MockBnetTestMixin, DjangoTestCase
from aid.test.data import gen_member
from common.utils import utcnow
from main.models import Region, Version, Ladder
from main.refetch import refetch_missing


class Test(MockBnetTestMixin, DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.db.delete_all()
        self.now = utcnow()
        self.today = self.now.date()
        self.s15 = self.db.create_season(id=15,
                                         start_date=self.date(days=-120),
                                         end_date=self.date(days=-21),
                                         version=Version.LOTV)
        self.s16 = self.db.create_season(id=16,
                                         start_date=self.date(days=-20),
                                         end_date=None,
                                         version=Version.LOTV)
        self.s17 = self.db.create_season(id=17,
                                         start_date=None,
                                         end_date=None,
                                         version=Version.LOTV)

    def refetch_missing(self):
        refetch_missing(region=Region.EU, max_retries=60, min_age=24, bnet_client=self.bnet)

    def test_fetch_replaces_500_with_200_cache(self):
        ladder = self.db.create_ladder(bid=100, season=self.s16, strangeness=Ladder.MISSING,
                                       member_count=None, max_points=None)
        cache = self.db.create_cache(bid=100, status=500, ladder=ladder, updated=self.datetime(days=-2))

        self.mock_fetch_ladder(status=200,
                               members=[gen_member(bid=300, points=104),
                                        gen_member(bid=301, points=102)])
        
        self.refetch_missing()

        ladder.refresh_from_db()
        cache.refresh_from_db()

        self.assertEqual(Ladder.GOOD, ladder.strangeness)
        self.assertEqual(2, ladder.member_count)
        self.assertEqual(104, ladder.max_points)

        self.assertEqual(200, cache.status)
        self.assertEqual(0, cache.retry_count)

    def test_fetch_does_not_refetch_if_refecth_count_is_too_high(self):
        ladder = self.db.create_ladder(bid=100, season=self.s16, strangeness=Ladder.MISSING)
        cache = self.db.create_cache(bid=100, status=500, ladder=ladder, updated=self.datetime(days=-2),
                                     retry_count=60)
        self.bnet.fetch_ladder = Mock()

        self.refetch_missing()

        self.assertEqual(0, self.bnet.fetch_ladder.call_count)

    def test_fetch_does_not_refetch_if_refetch_lt_24_hours_ago(self):
        ladder = self.db.create_ladder(bid=100, season=self.s16, strangeness=Ladder.MISSING)
        cache = self.db.create_cache(bid=100, status=500, ladder=ladder, updated=self.datetime(hours=-23))
        self.bnet.fetch_ladder = Mock()

        self.refetch_missing()

        self.assertEqual(0, self.bnet.fetch_ladder.call_count)



