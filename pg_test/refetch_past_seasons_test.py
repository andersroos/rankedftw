from unittest.mock import Mock

import aid.test.init_django_postgresql

from datetime import timedelta
from aid.test.base import DjangoTestCase, MockBnetTestMixin
from aid.test.data import gen_member, gen_api_ladder
from common.utils import utcnow
from main.models import Version, Region
from main.refetch import refetch_past_seasons


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
                                         end_date=self.date(days=-2),
                                         version=Version.LOTV)
        self.s17 = self.db.create_season(id=17,
                                         start_date=self.date(days=-1),
                                         end_date=None,
                                         version=Version.LOTV)

    def refetch_past_seasons(self):
        refetch_past_seasons(bnet_client=self.bnet, skip_fetch_new=True)

    def test_refetch_past_seasons_will_refetch_ladder_and_ranking_will_be_updated(self):
        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        l = self.db.create_ladder(bid=100, season=self.s15, max_points=20, updated=self.datetime(days=-30))

        c = self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s15, data_time=self.datetime(days=-21))

        self.db.create_ranking_data(data=[dict(team_id=t1.id, points=20, data_time=self.unix_time(days=-30))])
        self.db.update_ranking_stats()

        al = gen_api_ladder(data=[dict(team_id=t1.id, points=40)], bid=100)

        fetch_time = utcnow()
        self.mock_fetch_ladder(fetch_time=fetch_time, members=[gen_member(bid=p1.bid, points=40)])

        self.refetch_past_seasons()

        self.bnet.fetch_ladder.assert_called_once_with(self.s15.id, Region.EU, 100, timeout=20)

        l.refresh_from_db()
        r.refresh_from_db()

        self.assertTrue(abs(fetch_time - l.updated) < timedelta(hours=1))
        self.assertEqual(40, l.max_points)
        self.assertEqual({c.id}, {c.id for c in r.sources.all()})
        self.assert_team_ranks(r.id, dict(points=40))
        self.assertEqual(self.s15.end_time(), r.data_time)

    def test_refetch_past_seasons_skips_ladders_that_was_updated_recently(self):
        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        self.db.create_cache(bid=100)
        l = self.db.create_ladder(bid=100, season=self.s15, max_points=20, updated=self.datetime(days=-10))

        r = self.db.create_ranking(season=self.s15, data_time=self.s15.end_time())

        self.db.create_ranking_data(data=[dict(team_id=t1.id, points=20, data_time=self.unix_time(days=-30))])
        self.db.update_ranking_stats()

        self.refetch_past_seasons()

        l.refresh_from_db()
        r.refresh_from_db()

        self.assertEqual(self.datetime(days=-10), l.updated)
        self.assertEqual(20, l.max_points)
        self.assertEqual(1, r.sources.count())
        self.assert_team_ranks(r.id, dict(points=20))
        self.assertEqual(self.s15.end_time(), r.data_time)

    def test_skip_refetch_of_season_if_recently_closed(self):
        self.db.create_cache(bid=100)
        l = self.db.create_ladder(bid=100, season=self.s16, updated=self.datetime(days=-20))

        r = self.db.create_ranking(season=self.s16, data_time=self.datetime(days=-20))

        self.refetch_past_seasons()

        l.refresh_from_db()
        r.refresh_from_db()

        self.assertEqual(self.datetime(days=-20), l.updated)
        self.assertEqual(self.datetime(days=-20), r.data_time)
