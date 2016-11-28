import aid.test.init_django_postgresql

from aid.test.base import DjangoTestCase
from aid.test.data import gen_member
from common.utils import utcnow
from main.models import Region, Version
from main.update import countinously_update, UpdateManager
from rocky import Stop


class MockUpdateManager(UpdateManager):

    def __init__(self, update_until):
        self.update_until = update_until


class Test(DjangoTestCase):

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

        # Create ladders for existing seasons to make code eligible to switch to season.
        for bid in range(1500, 1510):
            self.db.create_ladder(bid=bid, season=self.s15)
        for bid in range(1600, 1610):
            self.db.create_ladder(bid=bid, season=self.s16)

    def countinously_update(self, update_manager=None, switch_hour=None):
        switch_hour = switch_hour or self.datetime(hours=2).hour
        
        def check_stop(throw=False):
            return True

        countinously_update(regions=[Region.EU], check_stop=check_stop, update_manager=update_manager,
                            switch_hour=switch_hour)

    def test_ranking_is_copied_from_previus_ranking_when_switching_ranking_but_not_season(self):
        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        p2 = self.db.create_player(name="sune")
        t2 = self.db.create_team()

        l100 = self.db.create_ladder(bid=100, season=self.s16, max_points=20, updated=self.datetime(days=-10))

        l101 = self.db.create_ladder(bid=101, season=self.s16, max_points=10, updated=self.datetime(days=-10))

        c100 = self.db.create_cache(bid=100, members=[gen_member(points=20, bid=p1.bid)])

        c101 = self.db.create_cache(bid=101, members=[gen_member(points=10, bid=p2.bid)])

        r = self.db.create_ranking(season=self.s16, created=self.datetime(hours=-48), data_time=self.datetime(days=-10))
        r.sources.add(c100, c101)

        self.db.create_ranking_data(data=[dict(team_id=t1.id, points=20, data_time=self.unix_time(days=-10)),
                                          dict(team_id=t2.id, points=10, data_time=self.unix_time(days=-10))])
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertNotEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            self.assertEqual({c100.id, c101.id}, {c.id for c in r.sources.all()})
            self.assertEqual(set(), {c.id for c in ranking.sources.all()} & {c.id for c in r.sources.all()})
            self.assertEqual({100, 101}, {c.bid for c in r.sources.all()})
            self.assertEqual({100, 101}, {c.bid for c in ranking.sources.all()})
            self.assertEqual(r.sources.get(bid=100).data, ranking.sources.get(bid=100).data)
            self.assertEqual(r.sources.get(bid=101).data, ranking.sources.get(bid=101).data)

            self.assert_team_ranks(ranking.id,
                                   dict(team_id=t1.id, points=20),
                                   dict(team_id=t2.id, points=10))

            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until))

    def test_ranking_is_craeted_fresh_when_switching_ranking_and_season(self):
        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        p2 = self.db.create_player(name="sune")
        t2 = self.db.create_team()

        l100 = self.db.create_ladder(bid=100, season=self.s15, max_points=20, updated=self.datetime(days=-30))

        l101 = self.db.create_ladder(bid=101, season=self.s15, max_points=10, updated=self.datetime(days=-30))

        c100 = self.db.create_cache(bid=100)
        c101 = self.db.create_cache(bid=101)

        r = self.db.create_ranking(season=self.s15, created=self.datetime(hours=-48), data_time=self.datetime(days=-30))
        r.sources.add(c100, c101)

        self.db.create_ranking_data(data=[dict(team_id=t1.id, points=20, data_time=self.unix_time(days=-30)),
                                          dict(team_id=t2.id, points=10, data_time=self.unix_time(days=-30))])
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertNotEqual(r.id, ranking.id)
            self.assertEqual(self.s15, r.season)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            self.assertEqual(set(), {c.id for c in ranking.sources.all()})
            self.assertEqual({100, 101}, {c.bid for c in r.sources.all()})
            self.assert_team_ranks(ranking.id)

            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until))

    def test_update_continues_with_current_ranking_if_created_lt_12_hours_ago(self):
        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s16, created=self.datetime(hours=-11))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until),
                                     switch_hour=self.now.hour)

    def test_update_continues_with_current_ranking_near_season_start(self):
        self.s16.start_date = self.date(days=-3)
        self.s16.save()
        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s16, created=self.datetime(days=-3))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until),
                                     switch_hour=self.now.hour)
            
    def test_update_siwtches_to_new_ranking_if_created_12_to_48_hours_ago_and_is_on_switch_hour(self):
        if self.datetime(minutes=1).hour != self.now.hour:
            # Only run this test if there is more than a minute left on the hour.
            return

        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s16, created=self.datetime(hours=-20))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertNotEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until),
                                     switch_hour=self.now.hour)

    def test_update_continues_with_current_ranking_if_created_12_to_48_hours_ago_but_is_not_on_switch_hour(self):
        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s16, created=self.datetime(hours=-20))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until))

    def test_update_switches_to_new_ranking_if_older_than_48_hours(self):
        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s16, created=self.datetime(hours=-48))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertNotEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until))

    def test_update_switches_to_new_ranking_regardless_of_age_if_new_seaaon_is_available(self):
        self.db.create_cache(bid=100)
        r = self.db.create_ranking(season=self.s15, created=self.datetime(hours=-1))
        self.db.create_ranking_data()
        self.db.update_ranking_stats()

        def update_until(ranking=None, until=None, **kwargs):
            self.assertNotEqual(r.id, ranking.id)
            self.assertEqual(self.s16, ranking.season)
            self.assertTrue(self.now < until)
            raise Stop()

        with self.assertRaises(Stop):
            self.countinously_update(update_manager=MockUpdateManager(update_until=update_until))
