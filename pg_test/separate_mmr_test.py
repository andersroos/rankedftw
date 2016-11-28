import aid.test.init_django_postgresql
from aid.test.data import gen_member

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from main.models import Season, Version, Team, Player, Mode, Race, Enums, Region, Cache
from main.models import League
from common.utils import utcnow


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db.create_season(id=29)
        self.db.create_cache()  # Ranking needs it for source.

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.db.delete_all(keep=[Season, Cache])
        self.db.create_ranking()
        self.ladder = self.db.create_ladder(bid=1, created=self.datetime(seconds=1))  # Always using same ladder.

    def test_no_update_of_player_or_team_if_worse_with_another_race(self):
        p1 = self.db.create_player(bid=301,
                                   league=League.PLATINUM,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id,
                                               league=League.PLATINUM,
                                               mmr=4000,
                                               race0=Race.ZERG)]),

        self.process_ladder(load=True,
                            mode=Mode.TEAM_1V1,
                            league=League.GOLD,
                            bid=301,
                            mmr=3000,
                            race=Race.TERRAN)

        p1.refresh_from_db()
        t1.refresh_from_db()

        self.assertEqual(League.PLATINUM, t1.league)
        self.assertEqual(Race.ZERG, t1.race0)
        self.assertEqual(League.PLATINUM, p1.league)
        self.assertEqual(Race.ZERG, p1.race)

    def test_update_of_player_and_team_if_better_with_another_race(self):
        p1 = self.db.create_player(bid=301,
                                   league=League.PLATINUM,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, mmr=3000, league=League.PLATINUM, race0=Race.ZERG)]),

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.MASTER,
                            mmr=5000,
                            bid=301,
                            race=Race.TERRAN)

        p1.refresh_from_db()
        t1.refresh_from_db()

        self.assertEqual(League.MASTER, t1.league)
        self.assertEqual(Race.TERRAN, t1.race0)
        self.assertEqual(League.MASTER, p1.league)
        self.assertEqual(Race.TERRAN, p1.race)

    def test_update_of_player_and_team_if_better_with_same_race(self):
        p1 = self.db.create_player(bid=301,
                                   league=League.PLATINUM,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, league=League.PLATINUM, mmr=3000, race0=Race.ZERG)]),

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.MASTER,
                            mmr=5000,
                            bid=301,
                            race=Race.ZERG)

        p1.refresh_from_db()
        t1.refresh_from_db()

        self.assertEqual(League.MASTER, t1.league)
        self.assertEqual(Race.ZERG, t1.race0)
        self.assertEqual(League.MASTER, p1.league)
        self.assertEqual(Race.ZERG, p1.race)

    def test_player_several_times_in_same_ladder_with_different_races(self):
        self.db.create_ranking()
        self.process_ladder(save=True,
                            mode=Mode.TEAM_1V1,
                            league=League.MASTER,
                            members=[
                                gen_member(bid=301, mmr=5090, race=Race.ZERG),
                                gen_member(bid=301, mmr=5080, race=Race.TERRAN),
                                gen_member(bid=301, mmr=5070, race=Race.PROTOSS),
                                gen_member(bid=301, mmr=5060, race=Race.RANDOM),
                            ])

        p1 = self.db.get(Player, bid=301)
        t1 = self.db.get(Team, member0=p1)

        self.assertEqual(League.MASTER, t1.league)
        self.assertEqual(Race.ZERG, t1.race0)
        self.assertEqual(League.MASTER, p1.league)
        self.assertEqual(Race.ZERG, p1.race)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t1.id, mmr=5090, race0=Race.ZERG, league=League.MASTER),
                               )

