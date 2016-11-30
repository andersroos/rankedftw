import aid.test.init_django_postgresql
from aid.test.base import DjangoTestCase
from aid.test.data import gen_member
from aid.test.db import Db
from common.utils import utcnow
from main.models import League
from main.models import Version, Mode, Region, Race


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.db = Db()

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.db.delete_all()
        self.db.create_season(id=1)
        self.db.create_ranking()

    def test_same_team_in_multiple_ladders_select_later_added_instance_and_disregards_times(self):
        # Given this, the ranker will have to rank ladders in fetch order to prevent overwriting data when teams
        # change ladder due to promotion/demotion.

        self.process_ladder(fetch_time=self.datetime(days=-200),
                            league=League.PLATINUM,
                            members=[
                                gen_member(bid=301,
                                           join_time=int(self.unix_time(days=-410))),
                                gen_member(bid=302,
                                           join_time=int(self.unix_time(days=-400))),
                                gen_member(bid=303,
                                           join_time=int(self.unix_time(days=-400)),
                                           points=20,
                                           wins=50),
                                gen_member(bid=304,
                                           join_time=int(self.unix_time(days=-400)),
                                           points=10,
                                           wins=40,
                                           losses=10),
                            ])
        
        self.process_ladder(league=League.GOLD,
                            fetch_time=self.datetime(days=-330),
                            members=[
                                gen_member(bid=302,
                                           join_time=int(self.unix_time(days=-410))),
                                gen_member(bid=303,
                                           join_time=int(self.unix_time(days=-410)),
                                           points=20,
                                           wins=60),
                                gen_member(bid=304,
                                           join_time=int(self.unix_time(days=-410)),
                                           points=10,
                                           wins=40,
                                           losses=20),
                            ])

        self.save_to_ranking()

        t1, t2, t3, t4 = self.db.get_teams_by_member0_bids(301, 302, 303, 304)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t1, region_count=4, region_rank=1, league=League.PLATINUM),
                               dict(team_id=t2, region_count=4, region_rank=2, league=League.GOLD),
                               dict(team_id=t3, region_count=4, region_rank=3, league=League.GOLD, wins=60),
                               dict(team_id=t4, region_count=4, region_rank=4, league=League.GOLD, wins=40, losses=20),
                               )

    def test_same_team_in_multiple_ladders_but_different_versions_and_all_are_in_the_ranking(self):
        self.process_ladder(version=Version.HOTS,
                            members=[
                                gen_member(bid=301, points=20),
                                gen_member(bid=302, points=10),
                            ])

        self.process_ladder(version=Version.WOL,
                            members=[
                                gen_member(bid=301, points=10),
                                gen_member(bid=302, points=20),
                            ])

        self.process_ladder(version=Version.LOTV,
                            members=[
                                gen_member(bid=301, points=40),
                                gen_member(bid=302, points=30),
                            ])

        self.save_to_ranking()

        t1, t2 = self.db.get_teams_by_member0_bids(301, 302)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t2, region_count=2, region_rank=1, points=20, version=Version.WOL),
                               dict(team_id=t1, region_count=2, region_rank=2, points=10, version=Version.WOL),
                               dict(team_id=t1, region_count=2, region_rank=1, points=20, version=Version.HOTS),
                               dict(team_id=t2, region_count=2, region_rank=2, points=10, version=Version.HOTS),
                               dict(team_id=t1, region_count=2, region_rank=1, points=40, version=Version.LOTV),
                               dict(team_id=t2, region_count=2, region_rank=2, points=30, version=Version.LOTV),
                               )

    def test_same_player_in_two_teams_multiple_ladders_but_different_modes_and_both_are_in_ranking(self):
        self.process_ladder(mode=Mode.RANDOM_4V4,
                            members=[
                                gen_member(bid=301, points=20),
                                gen_member(bid=302, points=10),
                            ])

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            members=[
                                gen_member(bid=301, points=10),
                                gen_member(bid=302, points=20),
                            ])

        self.save_to_ranking()

        t1, t2 = self.db.get_teams_by_member0_bids(301, 302, mode=Mode.RANDOM_3V3)
        t3, t4 = self.db.get_teams_by_member0_bids(301, 302, mode=Mode.RANDOM_4V4)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t2, region_count=2, region_rank=1, points=20, mode=Mode.RANDOM_3V3),
                               dict(team_id=t1, region_count=2, region_rank=2, points=10, mode=Mode.RANDOM_3V3),
                               dict(team_id=t3, region_count=2, region_rank=1, points=20, mode=Mode.RANDOM_4V4),
                               dict(team_id=t4, region_count=2, region_rank=2, points=10, mode=Mode.RANDOM_4V4),
                               )

    def test_different_versions_are_ranked_separately(self):
        self.process_ladder(version=Version.HOTS,
                            members=[
                                gen_member(points=20),
                                gen_member(points=10),
                            ])

        self.process_ladder(version=Version.WOL,
                            members=[
                                gen_member(points=21),
                                gen_member(points=11),
                            ])

        self.process_ladder(version=Version.LOTV,
                            members=[
                                gen_member(points=22),
                                gen_member(points=12),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(region_count=2, region_rank=1, world_rank=1, points=21, version=Version.WOL),
                               dict(region_count=2, region_rank=2, world_rank=2, points=11, version=Version.WOL),
                               dict(region_count=2, region_rank=1, world_rank=1, points=20, version=Version.HOTS),
                               dict(region_count=2, region_rank=2, world_rank=2, points=10, version=Version.HOTS),
                               dict(region_count=2, region_rank=1, world_rank=1, points=22, version=Version.LOTV),
                               dict(region_count=2, region_rank=2, world_rank=2, points=12, version=Version.LOTV),
                               )

    def test_different_modes_are_ranked_separatly(self):
        self.process_ladder(mode=Mode.TEAM_1V1,
                            members=[
                                gen_member(points=110),
                                gen_member(points=111),
                            ])

        self.process_ladder(mode=Mode.ARCHON,
                            members=[
                                gen_member(points=120),
                                gen_member(points=120),
                                gen_member(points=121),
                                gen_member(points=121),
                            ])

        self.process_ladder(mode=Mode.TEAM_2V2,
                            members=[
                                gen_member(points=220),
                                gen_member(points=220),
                                gen_member(points=221),
                                gen_member(points=221),
                            ])

        self.process_ladder(mode=Mode.RANDOM_2V2,
                            members=[
                                gen_member(points=210),
                                gen_member(points=211),
                            ])

        self.process_ladder(mode=Mode.TEAM_3V3,
                            members=[
                                gen_member(points=330),
                                gen_member(points=330),
                                gen_member(points=330),
                                gen_member(points=331),
                                gen_member(points=331),
                                gen_member(points=331),
                            ])

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            members=[
                                gen_member(points=310),
                                gen_member(points=311),
                            ])

        self.process_ladder(mode=Mode.TEAM_4V4,
                            members=[
                                gen_member(points=440),
                                gen_member(points=440),
                                gen_member(points=440),
                                gen_member(points=440),
                                gen_member(points=441),
                                gen_member(points=441),
                                gen_member(points=441),
                                gen_member(points=441),
                            ])

        self.process_ladder(mode=Mode.RANDOM_4V4,
                            members=[
                                gen_member(points=410),
                                gen_member(points=411),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(region_count=2, region_rank=1, world_rank=1, points=111, mode=Mode.TEAM_1V1),
                               dict(region_count=2, region_rank=2, world_rank=2, points=110, mode=Mode.TEAM_1V1),
                               dict(region_count=2, region_rank=1, world_rank=1, points=121, mode=Mode.ARCHON),
                               dict(region_count=2, region_rank=2, world_rank=2, points=120, mode=Mode.ARCHON),
                               dict(region_count=2, region_rank=1, world_rank=1, points=221, mode=Mode.TEAM_2V2),
                               dict(region_count=2, region_rank=2, world_rank=2, points=220, mode=Mode.TEAM_2V2),
                               dict(region_count=2, region_rank=1, world_rank=1, points=211, mode=Mode.RANDOM_2V2),
                               dict(region_count=2, region_rank=2, world_rank=2, points=210, mode=Mode.RANDOM_2V2),
                               dict(region_count=2, region_rank=1, world_rank=1, points=331, mode=Mode.TEAM_3V3),
                               dict(region_count=2, region_rank=2, world_rank=2, points=330, mode=Mode.TEAM_3V3),
                               dict(region_count=2, region_rank=1, world_rank=1, points=311, mode=Mode.RANDOM_3V3),
                               dict(region_count=2, region_rank=2, world_rank=2, points=310, mode=Mode.RANDOM_3V3),
                               dict(region_count=2, region_rank=1, world_rank=1, points=441, mode=Mode.TEAM_4V4),
                               dict(region_count=2, region_rank=2, world_rank=2, points=440, mode=Mode.TEAM_4V4),
                               dict(region_count=2, region_rank=1, world_rank=1, points=411, mode=Mode.RANDOM_4V4),
                               dict(region_count=2, region_rank=2, world_rank=2, points=410, mode=Mode.RANDOM_4V4),
                               )

    def test_ranking_world_region_league_tier_and_ladder_ranking_at_once_works_as_expected(self):
        self.process_ladder(region=Region.EU, league=League.SILVER,
                            members=[
                                gen_member(points=90),
                                gen_member(points=80),
                            ])

        self.process_ladder(region=Region.EU, league=League.GOLD,
                            members=[
                                gen_member(points=77),
                                gen_member(points=33),
                            ])

        self.process_ladder(region=Region.AM, league=League.GOLD,
                            members=[
                                gen_member(points=95),
                                gen_member(points=10),
                            ])

        self.process_ladder(region=Region.KR, league=League.GRANDMASTER,
                            members=[
                                gen_member(points=1),
                            ])

        self.process_ladder(region=Region.EU, league=League.SILVER, tier=1,
                            members=[
                                gen_member(points=90),
                                gen_member(points=80),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(world_rank=1,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    world_count=9, region_count=1, league_count=1, ladder_count=1,
                                    points=1, region=Region.KR, league=League.GRANDMASTER),
                               dict(world_rank=2,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    world_count=9, region_count=2, league_count=2, ladder_count=2,
                                    points=95, region=Region.AM, league=League.GOLD),
                               dict(world_rank=3,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    world_count=9, region_count=6, league_count=2, ladder_count=2,
                                    points=77, region=Region.EU, league=League.GOLD),
                               dict(world_rank=4,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    world_count=9, region_count=6, league_count=2, ladder_count=2,
                                    points=33, region=Region.EU, league=League.GOLD),
                               dict(world_rank=5,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    world_count=9, region_count=2, league_count=2, ladder_count=2,
                                    points=10, region=Region.AM, league=League.GOLD),
                               dict(world_rank=6,  region_rank=3,  league_rank=1,  ladder_rank=1, tier=0,
                                    world_count=9, region_count=6, league_count=4, ladder_count=2,
                                    points=90, region=Region.EU, league=League.SILVER),
                               dict(world_rank=7,  region_rank=4,  league_rank=2,  ladder_rank=2, tier=0,
                                    world_count=9, region_count=6, league_count=4, ladder_count=2,
                                    points=80, region=Region.EU, league=League.SILVER),
                               dict(world_rank=8,  region_rank=5,  league_rank=3,  ladder_rank=1, tier=1,
                                    world_count=9, region_count=6, league_count=4, ladder_count=2,
                                    points=90, region=Region.EU, league=League.SILVER),
                               dict(world_rank=9,  region_rank=6,  league_rank=4,  ladder_rank=2, tier=1,
                                    world_count=9, region_count=6, league_count=4, ladder_count=2,
                                    points=80, region=Region.EU, league=League.SILVER))

    def test_region_ranking_does_rank_calculation_correctly_when_teams_have_same_points(self):
        self.process_ladder(members=[
            gen_member(points=90),
            gen_member(points=90),
        ])

        self.process_ladder(members=[
            gen_member(points=90),
            gen_member(points=10),
        ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(region_rank=1, world_rank=1, points=90),
                               dict(region_rank=1, world_rank=1, points=90),
                               dict(region_rank=1, world_rank=1, points=90),
                               dict(region_rank=4, world_rank=4, points=10),
                               )

    def test_simple_world_ranking(self):
        self.process_ladder(region=Region.EU, league=League.GOLD,
                            members=[
                                gen_member(points=90),
                                gen_member(points=80),
                            ])

        self.process_ladder(region=Region.AM, league=League.GOLD,
                            members=[
                                gen_member(points=95),
                                gen_member(points=10),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(world_count=4, world_rank=1, points=95),
                               dict(world_count=4, world_rank=2, points=90),
                               dict(world_count=4, world_rank=3, points=80),
                               dict(world_count=4, world_rank=4, points=10),
                               )

    def test_simple_region_ranking(self):
        self.process_ladder(league=League.GOLD,
                            members=[
                                gen_member(points=90),
                                gen_member(points=80),
                            ])

        self.process_ladder(league=League.SILVER,
                            members=[
                                gen_member(points=95),
                                gen_member(points=10),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(region_count=4, region_rank=1, points=90, league=League.GOLD),
                               dict(region_count=4, region_rank=2, points=80, league=League.GOLD),
                               dict(region_count=4, region_rank=3, points=95, league=League.SILVER),
                               dict(region_count=4, region_rank=4, points=10, league=League.SILVER),
                               )

    def test_simple_league_ranking(self):
        self.process_ladder(members=[
            gen_member(points=90),
            gen_member(points=80),
        ])

        self.process_ladder(members=[
            gen_member(points=95),
            gen_member(points=10),
        ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(league_count=4, league_rank=1, points=95),
                               dict(league_count=4, league_rank=2, points=90),
                               dict(league_count=4, league_rank=3, points=80),
                               dict(league_count=4, league_rank=4, points=10),
                               )

    def test_simple_ladder_ranking(self):
        self.process_ladder(members=[
            gen_member(points=90),
            gen_member(points=80),
        ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(ladder_count=2, ladder_rank=1, points=90),
                               dict(ladder_count=2, ladder_rank=2, points=80),
                               )

    def test_updating_with_members_at_end_or_beginning_or_mid_works(self):
        self.process_ladder(members=[
            gen_member(bid=302, points=40),
            gen_member(bid=304, points=20),
        ])

        self.process_ladder(members=[
            gen_member(bid=301, points=50),
            gen_member(bid=303, points=30),
            gen_member(bid=305, points=10),
        ])

        self.save_to_ranking()

        t1, t2, t3, t4, t5 = self.db.get_teams_by_member0_bids(301, 302, 303, 304, 305)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t1, points=50),
                               dict(team_id=t2, points=40),
                               dict(team_id=t3, points=30),
                               dict(team_id=t4, points=20),
                               dict(team_id=t5, points=10),
                               )

    def test_updating_with_replacing_members_in_different_order_works(self):
        self.process_ladder(members=[
            gen_member(bid=301, points=50),
            gen_member(bid=302, points=30),
            gen_member(bid=303, points=10),
        ])

        self.process_ladder(members=[
            gen_member(bid=303, points=60),
            gen_member(bid=302, points=40),
            gen_member(bid=301, points=20),
        ])

        self.save_to_ranking()

        t1, t2, t3 = self.db.get_teams_by_member0_bids(301, 302, 303)

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t3, points=60),
                               dict(team_id=t2, points=40),
                               dict(team_id=t1, points=20),
                               )

    def test_trigger_bug_insert_before_replace_will_make_double_insert(self):

        p1 = self.db.create_player(bid=301)
        t1 = self.db.create_team(member0=p1)

        p2 = self.db.create_player(bid=302)
        t2 = self.db.create_team(member0=p2)

        p3 = self.db.create_player(bid=303)
        t3 = self.db.create_team(member0=p3)

        self.process_ladder(members=[
            gen_member(bid=301),
            gen_member(bid=303),
        ])

        self.process_ladder(members=[
            gen_member(bid=302),
            gen_member(bid=303),
        ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t1.id),
                               dict(team_id=t2.id),
                               dict(team_id=t3.id),
                               sort=False
                               )

    def test_trigger_insert_replace_and_add_at_the_same_time(self):

        p1 = self.db.create_player(bid=301)
        t1 = self.db.create_team(member0=p1)

        p2 = self.db.create_player(bid=302)
        t2 = self.db.create_team(member0=p2)

        p3 = self.db.create_player(bid=303)
        t3 = self.db.create_team(member0=p3)

        p4 = self.db.create_player(bid=304)
        t4 = self.db.create_team(member0=p4)

        p5 = self.db.create_player(bid=305)
        t5 = self.db.create_team(member0=p5)

        p6 = self.db.create_player(bid=306)
        t6 = self.db.create_team(member0=p6)

        self.process_ladder(members=[
            gen_member(bid=302, points=10),
            gen_member(bid=305),
        ])

        self.process_ladder(members=[
            gen_member(bid=301),
            gen_member(bid=302, points=20),
            gen_member(bid=303),
            gen_member(bid=304),
            gen_member(bid=306),
        ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(team_id=t1.id),
                               dict(team_id=t2.id, points=20),
                               dict(team_id=t3.id),
                               dict(team_id=t4.id),
                               dict(team_id=t5.id),
                               dict(team_id=t6.id),
                               sort=False
                               )

    def test_worst_race_is_filtered_if_team_has_several_races__separate_mmr_test(self):
        self.db.create_season(id=29)
        self.process_ladder(members=[
            gen_member(points=99, mmr=99, bid=1, race=Race.TERRAN),
            gen_member(points=80, mmr=80, bid=1, race=Race.RANDOM),
        ])
        
        self.process_ladder(league=League.GOLD,
                            members=[
                                gen_member(points=90, mmr=90, bid=1, race=Race.ZERG),
                                gen_member(points=70, mmr=70, bid=1, race=Race.PROTOSS),
                            ])
                            
        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(ladder_count=1, region_count=1, region_rank=1, points=99, mmr=99, race0=Race.TERRAN,
                                    league=League.GOLD),
                               )

    def test_gm_is_using_points_before_season_28(self):
        self.db.create_season(id=27)
        self.db.create_ranking()

        self.process_ladder(league=League.GRANDMASTER, region=Region.EU,
                            members=[
                                gen_member(points=80),
                                gen_member(points=10),
                            ])

        self.process_ladder(league=League.GRANDMASTER, region=Region.KR,
                            members=[
                                gen_member(points=99),
                                gen_member(points=70),
                                gen_member(points=70),
                            ])

        self.process_ladder(league=League.GRANDMASTER, region=Region.AM,
                            members=[
                                gen_member(points=200),
                                gen_member(points=98),
                            ])

        self.save_to_ranking()

        self.assert_team_ranks(self.db.ranking.id,
                               dict(world_rank=1,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    points=200, region=Region.AM),
                               dict(world_rank=2,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    points=99, region=Region.KR),
                               dict(world_rank=3,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    points=98, region=Region.AM),
                               dict(world_rank=4,  region_rank=1,  league_rank=1,  ladder_rank=1,
                                    points=80, region=Region.EU),
                               dict(world_rank=5,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    points=70, region=Region.KR),
                               dict(world_rank=5,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    points=70, region=Region.KR),
                               dict(world_rank=7,  region_rank=2,  league_rank=2,  ladder_rank=2,
                                    points=10, region=Region.EU))

