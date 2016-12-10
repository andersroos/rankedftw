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

    def test_all_races_and_all_versions_are_present_at_end_of_ranking(self):
        teams = [self.t2, self.t3, self.t4, self.t5, self.t1]
        self.db.create_ranking()
        data = []
        mmr = 0
        for team in teams:
            mmr += 100
            for version in Version.ids:
                for race in Race.ranking_ids:
                    if race != Race.UNKNOWN:
                        data.append(dict(team_id=team.id, race0=race, mmr=mmr + race, version=version))
        self.db.create_ranking_data(raw=False, data=data)

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(4, len(rankings))

        self.assertEqual(Race.ZERG,    rankings[0]["race0"])
        self.assertEqual(Race.PROTOSS, rankings[1]["race0"])
        self.assertEqual(Race.TERRAN,  rankings[2]["race0"])
        self.assertEqual(Race.RANDOM,  rankings[3]["race0"])

        self.assertEqual(500, rankings[0]["mmr"])
        self.assertEqual(501, rankings[1]["mmr"])
        self.assertEqual(502, rankings[2]["mmr"])
        self.assertEqual(503, rankings[3]["mmr"])

        self.assertEqual(Version.LOTV, rankings[0]["version"])
        self.assertEqual(Version.LOTV, rankings[1]["version"])
        self.assertEqual(Version.LOTV, rankings[2]["version"])
        self.assertEqual(Version.LOTV, rankings[3]["version"])

        self.assertEqual(False, rankings[0]["best_race"])
        self.assertEqual(False, rankings[1]["best_race"])
        self.assertEqual(False, rankings[2]["best_race"])
        self.assertEqual(True,  rankings[3]["best_race"])

    def test_all_races_and_all_versions_are_present_at_beginning_of_ranking(self):
        teams = [self.t1, self.t2, self.t3, self.t4, self.t5]
        self.db.create_ranking()
        data = []
        mmr = 0
        for team in teams:
            mmr += 100
            for version in Version.ids:
                for race in Race.ranking_ids:
                    if race != Race.UNKNOWN:
                        data.append(dict(team_id=team.id, race0=race, mmr=mmr + race, version=version))
        self.db.create_ranking_data(raw=False, data=data)

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(4, len(rankings))

        self.assertEqual(Race.ZERG,    rankings[0]["race0"])
        self.assertEqual(Race.PROTOSS, rankings[1]["race0"])
        self.assertEqual(Race.TERRAN,  rankings[2]["race0"])
        self.assertEqual(Race.RANDOM,  rankings[3]["race0"])

        self.assertEqual(100, rankings[0]["mmr"])
        self.assertEqual(101, rankings[1]["mmr"])
        self.assertEqual(102, rankings[2]["mmr"])
        self.assertEqual(103, rankings[3]["mmr"])

        self.assertEqual(Version.LOTV, rankings[0]["version"])
        self.assertEqual(Version.LOTV, rankings[1]["version"])
        self.assertEqual(Version.LOTV, rankings[2]["version"])
        self.assertEqual(Version.LOTV, rankings[3]["version"])

        self.assertEqual(False, rankings[0]["best_race"])
        self.assertEqual(False, rankings[1]["best_race"])
        self.assertEqual(False, rankings[2]["best_race"])
        self.assertEqual(True,  rankings[3]["best_race"])

    def test_finds_one_wol_race_among_many(self):
        teams = [self.t2, self.t3, self.t4, self.t5]
        self.db.create_ranking()
        data = []
        mmr = 0
        for team in teams:
            mmr += 100
            for version in Version.ids:
                for race in Race.ranking_ids:
                    if race != Race.UNKNOWN:
                        data.append(dict(team_id=team.id, race0=race, mmr=mmr + race, version=version))
        data.append(dict(team_id=self.t1.id, race0=Race.ZERG, mmr=120, version=Version.WOL))

        self.db.create_ranking_data(raw=False, data=data)

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))

        self.assertEqual(Race.ZERG, rankings[0]["race0"])
        self.assertEqual(120, rankings[0]["mmr"])
        self.assertEqual(Version.WOL, rankings[0]["version"])
        self.assertEqual(True, rankings[0]["best_race"])
