import json
import gc

import aid.test.init_django_postgresql

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from main.models import *
from logging import getLogger
from django.conf import settings
from lib import sc2

logger = getLogger('django')
sc2.set_logger(logger)


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db_name = settings.DATABASES['default']['NAME']

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.t1, self.t2, self.t3 = self.db.create_teams(count=3)

    def setUp(self):
        super().setUp()
        self.db.clear_defaults()
        self.db.delete_all(keep=[Cache, Ladder, Team, Player])
        self.db.create_season(version=Version.HOTS)
        self.c = sc2.Get(self.db_name, Enums.INFO, 0)

    def tearDown(self):
        # Null and garbage collect to disconnect c++ code from the database.
        self.c = None
        gc.collect()
        super().tearDown()

    def test_create_stats_from_empty_ranking_data(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
        ])
        self.db.update_ranking_stats()

        for mode_id in Mode.stat_v1_ids:
            stats, = json.loads(self.c.ranking_stats(mode_id))
            self.assertEqual(0, sum(stats['data']))
            self.assertEqual(RankingStats.V1, stats['stat_version'])
            self.assertEqual(self.db.season.id, stats['season_id'])
            self.assertEqual(Version.HOTS, stats['season_version'])
            self.assertEqual(self.db.ranking.id, stats['id'])
            self.assertEqual(RankingStats.V1_DATA_COUNT * RankingStats.V1_DATA_SIZE, len(stats['data']))

    def test_create_stats_from_lotv_season_gets_correct_version(self):
        self.db.create_season(id=17, version=Version.LOTV)
        self.db.create_ranking()
        self.db.create_ranking_data(data=[])
        self.db.update_ranking_stats()

        stats, = json.loads(self.c.ranking_stats(Mode.TEAM_1V1))

        self.assertEqual(RankingStats.V1, stats['stat_version'])
        self.assertEqual(self.db.season.id, stats['season_id'])
        self.assertEqual(Version.LOTV, stats['season_version'])
        self.assertEqual(self.db.ranking.id, stats['id'])
        self.assertEqual(RankingStats.V1_DATA_COUNT * RankingStats.V1_DATA_SIZE, len(stats['data']))
        self.assertEqual(0, sum(stats['data']))

    def test_create_stats_from_lotv_season_with_archon_mode_is_calculated_correctly(self):
        self.db.default_ranking_data__data = dict(
            mode=Mode.TEAM_1V1,
            version=Version.LOTV,
            region=Region.EU,
            league=League.GOLD,
            race0=Race.ZERG
        )

        self.db.create_season(id=17, version=Version.LOTV)
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(wins=10, losses=10, points=10.0, race0=Race.ZERG, mode=Mode.RANDOM_2V2),
            dict(wins=20, losses=21, points=22.0, race0=Race.TERRAN, mode=Mode.ARCHON),
            dict(wins=30, losses=31, points=32.0, race0=Race.PROTOSS, mode=Mode.TEAM_1V1),
        ])
        self.db.update_ranking_stats()

        stats, = json.loads(self.c.ranking_stats(Mode.RANDOM_2V2))

        self.assertEqual(1 + 10 + 10 + 10, sum(stats['data']))
        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.LOTV_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 10, 10, 10], stats['data'][index: index + 4])

        stats, = json.loads(self.c.ranking_stats(Mode.ARCHON))

        self.assertEqual(1 + 20 + 21 + 22, sum(stats['data']))
        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.LOTV_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.TERRAN_INDEX)
        self.assertEqual([1, 20, 21, 22], stats['data'][index: index + 4])

        stats, = json.loads(self.c.ranking_stats(Mode.TEAM_1V1))

        self.assertEqual(1 + 30 + 31 + 32, sum(stats['data']))
        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.LOTV_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.PROTOSS_INDEX)
        self.assertEqual([1, 30, 31, 32], stats['data'][index: index + 4])

    def test_create_stats_with_different_archon_versions_is_calculated_correctly(self):
        self.db.default_ranking_data__data = dict(
            mode=Mode.ARCHON,
            version=Version.LOTV,
            region=Region.EU,
            league=League.GOLD,
            race0=Race.ZERG
        )

        self.db.create_season(id=17, version=Version.LOTV)
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(wins=10, losses=10, points=10.0, version=Version.WOL),
            dict(wins=20, losses=21, points=22.0, version=Version.HOTS),
            dict(wins=30, losses=31, points=32.0, version=Version.LOTV),
        ])
        self.db.update_ranking_stats()

        stats, = json.loads(self.c.ranking_stats(Mode.ARCHON))

        self.assertEqual(3 + 60 + 62 + 64, sum(stats['data']))

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.WOL_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 10, 10, 10], stats['data'][index: index + 4])

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 20, 21, 22], stats['data'][index: index + 4])

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.LOTV_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 30, 31, 32], stats['data'][index: index + 4])

    def test_create_stats_using_two_teams_that_sums(self):
        self.db.default_ranking_data__data = dict(
            mode=Mode.TEAM_1V1,
            version=Version.HOTS,
            region=Region.EU,
            league=League.GOLD,
            race0=Race.ZERG
        )
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(wins=10, losses=10, points=10.0),
            dict(wins=20, losses=21, points=22.0),
        ])
        self.db.update_ranking_stats()

        for mode_id in Mode.stat_v1_ids:
            if mode_id == Mode.TEAM_1V1:
                continue
            stats, = json.loads(self.c.ranking_stats(mode_id))
            self.assertEqual(0, sum(stats['data']))

        stats, = json.loads(self.c.ranking_stats(Mode.TEAM_1V1))

        self.assertEqual(RankingStats.V1, stats['stat_version'])
        self.assertEqual(self.db.season.id, stats['season_id'])
        self.assertEqual(Version.HOTS, stats['season_version'])
        self.assertEqual(self.db.ranking.id, stats['id'])
        self.assertEqual(RankingStats.V1_DATA_COUNT * RankingStats.V1_DATA_SIZE, len(stats['data']))
        self.assertEqual(2 + 30 + 31 + 32, sum(stats['data']))

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)

        self.assertEqual([2, 30, 31, 32], stats['data'][index: index + 4])

    def test_creating_stats_for_three_teams_with_different_parameters(self):
        self.db.default_ranking_data__data = dict(
            mode=Mode.RANDOM_4V4,
            version=Version.HOTS,
            region=Region.EU,
            league=League.GOLD,
            race0=Race.ZERG
        )
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, wins=10, losses=11, points=12.0, region=Region.CN),
            dict(team_id=self.t2.id, wins=20, losses=21, points=22.0, race0=Race.TERRAN),
            dict(team_id=self.t3.id, wins=30, losses=31, points=32.0, league=League.PLATINUM),
        ])
        self.db.update_ranking_stats()

        for mode_id in Mode.stat_v1_ids:
            if mode_id == Mode.RANDOM_4V4:
                continue
            stats, = json.loads(self.c.ranking_stats(mode_id))
            self.assertEqual(0, sum(stats['data']))

        stats, = json.loads(self.c.ranking_stats(Mode.RANDOM_4V4))

        self.assertEqual(3 + 60 + 63 + 66, sum(stats['data']))

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX,
                                          Region.CN_INDEX, League.GOLD_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 10, 11, 12], stats['data'][index: index + 4])

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX,
                                          Region.EU_INDEX, League.GOLD_INDEX, Race.TERRAN_INDEX)
        self.assertEqual([1, 20, 21, 22], stats['data'][index: index + 4])

        index = RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX,
                                          Region.EU_INDEX, League.PLATINUM_INDEX, Race.ZERG_INDEX)
        self.assertEqual([1, 30, 31, 32], stats['data'][index: index + 4])

