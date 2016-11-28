import json

import aid.test.init_django_postgresql

from aid.test.db import Db

from aid.test.base import DjangoTestCase

from django.test import Client
from main.models import Version, League, RankingStats, Region, Race, Cache, Ladder, Season
from main.views.base import rankings_view_client


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.db.create_season()

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Cache, Ladder, Season])
        self.c = Client()

    def tearDown(self):
        rankings_view_client.close()
        super(Test, self).tearDown()

    def test_view_league_stats(self):
        self.db.create_player()
        t1 = self.db.create_team()

        self.db.create_player()
        t2 = self.db.create_team()

        self.db.create_player()
        t3 = self.db.create_team()

        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=t1.id, league=League.GOLD,     wins=11, losses=10, points=20),
            dict(team_id=t2.id, league=League.PLATINUM, wins=21, losses=20, points=40),
            dict(team_id=t3.id, league=League.PLATINUM, wins=31, losses=30, points=50),
        ])
        self.db.update_ranking_stats()

        response = self.c.get('/stats/leagues/1v1/')
        self.assertEqual(200, response.status_code)
        self.assertIn('1v1 League Distribution', response.content.decode('utf-8'))

        response = self.c.get('/stats/raw/11/')
        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(1, len(content))

        data = content[0]['data']

        def get_stat(league_index, type_index):
            return data[RankingStats.raw_v1_index(RankingStats.V1_DATA_SIZE, Version.HOTS_INDEX, Region.EU_INDEX,
                                                  league_index, Race.ZERG_INDEX)
                        + type_index]

        self.assertEqual(1,  get_stat(League.GOLD_INDEX,     RankingStats.V1_COUNT_INDEX))
        self.assertEqual(11, get_stat(League.GOLD_INDEX,     RankingStats.V1_WINS_INDEX))
        self.assertEqual(10, get_stat(League.GOLD_INDEX,     RankingStats.V1_LOSSES_INDEX))
        self.assertEqual(20, get_stat(League.GOLD_INDEX,     RankingStats.V1_POINT_INDEX))
        self.assertEqual(2,  get_stat(League.PLATINUM_INDEX, RankingStats.V1_COUNT_INDEX))
        self.assertEqual(52, get_stat(League.PLATINUM_INDEX, RankingStats.V1_WINS_INDEX))
        self.assertEqual(50, get_stat(League.PLATINUM_INDEX, RankingStats.V1_LOSSES_INDEX))
        self.assertEqual(90, get_stat(League.PLATINUM_INDEX, RankingStats.V1_POINT_INDEX))
