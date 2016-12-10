import gc

import aid.test.init_django_postgresql

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from lib import sc2
from django.conf import settings

from main.models import Race, Ladder, Season, Cache, Version, Enums


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.db.create_season(id=29, version=Version.LOTV)
        self.t1, self.t2, self.t3, self.t4, self.t5 = self.db.create_teams(count=5)

    def setUp(self):
        super().setUp()
        self.db.clear_defaults()
        self.db.delete_all(keep=[Season, Ladder, Cache])
        self.c = sc2.Get(settings.DATABASES['default']['NAME'], Enums.INFO, 0)

    def tearDown(self):
        # Null and garbage collect to disconnect c++ code from the database (RAII).
        self.c = None
        gc.collect()
        super().tearDown()

    def test_all_races_are_found_and_returned(self):

        self.db.create_ranking()
        self.db.create_ranking_data(raw=False, data=[
            dict(team_id=self.t1.id, race0=Race.UNKNOWN, mmr=1),
            dict(team_id=self.t1.id, race0=Race.ZERG,    mmr=2),
            dict(team_id=self.t1.id, race0=Race.PROTOSS, mmr=6),
            dict(team_id=self.t1.id, race0=Race.TERRAN,  mmr=5),
            dict(team_id=self.t1.id, race0=Race.RANDOM,  mmr=4),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)
        self.assertEqual(5, len(rankings))

        self.assertEqual(Race.UNKNOWN, rankings[0]["race0"])
        self.assertEqual(Race.ZERG,    rankings[1]["race0"])
        self.assertEqual(Race.PROTOSS, rankings[2]["race0"])
        self.assertEqual(Race.TERRAN,  rankings[3]["race0"])
        self.assertEqual(Race.RANDOM,  rankings[4]["race0"])

        self.assertEqual(False, rankings[0]["best_race"])
        self.assertEqual(False, rankings[1]["best_race"])
        self.assertEqual(True,  rankings[2]["best_race"])
        self.assertEqual(False, rankings[3]["best_race"])
        self.assertEqual(False, rankings[4]["best_race"])
