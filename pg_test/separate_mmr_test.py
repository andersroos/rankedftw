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

    def test_same_1v1_can_have_multiple_rankings_with_different_races(self):
        self.process_ladder(league=League.SILVER,
                            members=[
                                gen_member(bid=1, mmr=50, race=Race.TERRAN),
                                gen_member(bid=1, mmr=40, race=Race.ZERG),
                                gen_member(bid=1, mmr=30, race=Race.RANDOM),
                            ])

        self.process_ladder(league=League.GOLD,
                            members=[
                                gen_member(bid=1, mmr=90, race=Race.TERRAN),
                                gen_member(bid=1, mmr=80, race=Race.PROTOSS),
                                gen_member(bid=1, mmr=70, race=Race.ZERG),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(
            self.db.ranking.id,
            dict(region_count=4, region_rank=1, mmr=90, race0=Race.TERRAN,  race3=9, league=League.GOLD),
            dict(region_count=4, region_rank=2, mmr=80, race0=Race.PROTOSS, race3=8, league=League.GOLD),
            dict(region_count=4, region_rank=3, mmr=70, race0=Race.ZERG,    race3=8, league=League.GOLD),
            dict(region_count=4, region_rank=4, mmr=30, race0=Race.RANDOM,  race3=8, league=League.SILVER),
        )

    def test_same_1v1_can_have_multiple_rankings_with_different_races_among_other_players(self):
        self.process_ladder(league=League.SILVER,
                            members=[
                                gen_member(bid=2, mmr=50, race=Race.ZERG),
                                gen_member(bid=1, mmr=40, race=Race.TERRAN),
                                gen_member(bid=3, mmr=30, race=Race.RANDOM),
                            ])

        self.process_ladder(league=League.GOLD,
                            members=[
                                gen_member(bid=1, mmr=90, race=Race.ZERG),
                                gen_member(bid=4, mmr=80, race=Race.PROTOSS),
                                gen_member(bid=5, mmr=70, race=Race.TERRAN),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(
            self.db.ranking.id,
            dict(region_count=6, region_rank=1, mmr=90, race0=Race.ZERG,    race3=9, league=League.GOLD),
            dict(region_count=6, region_rank=2, mmr=80, race0=Race.PROTOSS, race3=9, league=League.GOLD),
            dict(region_count=6, region_rank=3, mmr=70, race0=Race.TERRAN,  race3=9, league=League.GOLD),
            dict(region_count=6, region_rank=4, mmr=50, race0=Race.ZERG,    race3=9, league=League.SILVER),
            dict(region_count=6, region_rank=5, mmr=40, race0=Race.TERRAN,  race3=8, league=League.SILVER),
            dict(region_count=6, region_rank=6, mmr=30, race0=Race.RANDOM,  race3=9, league=League.SILVER),
        )

    def test_same_random_2v2__can_not_have_multiple_rankings_with_different_races(self):
        
        self.process_ladder(league=League.SILVER,
                            mode=Mode.RANDOM_2V2,
                            members=[
                                gen_member(bid=1, mmr=40, race=Race.TERRAN),
                            ])

        self.process_ladder(league=League.GOLD,
                            mode=Mode.RANDOM_2V2,
                            members=[
                                gen_member(bid=1, mmr=90, race=Race.ZERG),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(
            self.db.ranking.id,
            dict(region_count=1, region_rank=1, mmr=90, race0=Race.ZERG, league=League.GOLD),
        )

