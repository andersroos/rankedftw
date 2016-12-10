import gc

import aid.test.init_django_postgresql

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from main.models import *
from lib import sc2
from django.conf import settings


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.db.create_season(id=27, version=Version.LOTV)
        self.t1, self.t2, self.t3 = self.db.create_teams(count=3)

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

    def test_get_team_from_ranking_with_only_one_team(self):

        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=8912),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(8912, rankings[0]["points"])

        rankings = self.c.rankings_for_team(self.t1.id + 1)

        self.assertEqual(0, len(rankings))

    def test_get_team_from_tanking_with_two_different_teams(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=8912),
            dict(team_id=self.t2.id, points=1234),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(8912, rankings[0]["points"])

        rankings = self.c.rankings_for_team(self.t2.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(1234, rankings[0]["points"])

    def test_get_team_from_ranking_with_two_rankings_from_same_team_but_different_versions_1(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=8912, version=Version.WOL),
            dict(team_id=self.t1.id, points=1234, version=Version.HOTS),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(1234, rankings[0]["points"])
        self.assertEqual(Version.HOTS, rankings[0]["version"])

    def test_get_team_from_ranking_with_two_rankings_from_same_team_but_different_versions_2(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=8912, version=Version.WOL),
            dict(team_id=self.t1.id, points=1111, version=Version.LOTV),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(1111, rankings[0]["points"])
        self.assertEqual(Version.LOTV, rankings[0]["version"])

    def test_get_team_from_ranking_with_two_rankings_from_same_team_but_different_versions_3(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=1234, version=Version.HOTS),
            dict(team_id=self.t1.id, points=1111, version=Version.LOTV),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(1111, rankings[0]["points"])
        self.assertEqual(Version.LOTV, rankings[0]["version"])

    def test_get_team_from_ranking_with_tree_rankings_from_same_team_but_different_versions(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=8912, version=Version.WOL),
            dict(team_id=self.t1.id, points=1234, version=Version.HOTS),
            dict(team_id=self.t1.id, points=2222, version=Version.LOTV),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(2222, rankings[0]["points"])
        self.assertEqual(Version.LOTV, rankings[0]["version"])

    def test_get_from_ranking_with_tree_teams_of_which_one_has_all_versions_one_has_two_versions_and_one_only_wol(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t1.id, points=1, version=Version.WOL),
            dict(team_id=self.t2.id, points=2, version=Version.WOL),
            dict(team_id=self.t3.id, points=3, version=Version.WOL),
            dict(team_id=self.t2.id, points=4, version=Version.HOTS),
            dict(team_id=self.t3.id, points=5, version=Version.HOTS),
            dict(team_id=self.t3.id, points=6, version=Version.LOTV),
        ])

        rankings = self.c.rankings_for_team(self.t1.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(Version.WOL, rankings[0]["version"])
        self.assertEqual(1, rankings[0]["points"])

        rankings = self.c.rankings_for_team(self.t2.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(Version.HOTS, rankings[0]["version"])
        self.assertEqual(4, rankings[0]["points"])

        rankings = self.c.rankings_for_team(self.t3.id)

        self.assertEqual(1, len(rankings))
        self.assertEqual(Version.LOTV, rankings[0]["version"])
        self.assertEqual(6, rankings[0]["points"])

