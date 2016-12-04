import json

import aid.test.init_django_postgresql

from aid.test.db import Db

from aid.test.base import DjangoTestCase

from django.test import Client

from main.battle_net import NO_MMR
from main.models import Player, Version, Team, RankingData, Ranking, Cache, Ladder, Season
from main.views.base import rankings_view_client


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Cache, Ladder])
        self.db.create_season()
        self.c = Client()

    def tearDown(self):
        rankings_view_client.close()
        super(Test, self).tearDown()

    def test_view_team(self):
        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        self.db.create_player(name="sune")
        t2 = self.db.create_team()

        r1 = self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, ladder_rank=10, version=Version.WOL)])

        r2 = self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, ladder_rank=11, version=Version.HOTS),
                                          dict(team_id=t2.id, ladder_rank=8, version=Version.HOTS)])

        r3 = self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, ladder_rank=12, version=Version.HOTS),
                                          dict(team_id=t1.id, ladder_rank=6, version=Version.WOL)])

        r4 = self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=t1.id, ladder_rank=13, version=Version.LOTV),
                                          dict(team_id=t1.id, ladder_rank=4, version=Version.HOTS)])

        response = self.c.get('/team/%d/' % t1.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(t1, response.context['team'])
        self.assertEqual([p1], response.context['members'])

        response = self.c.get('/team/%d/rankings/' % t1.id)

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(4, len(data))

        data0 = data[0]

        self.assertEqual(r1.id, data0['id'])
        self.assertEqual(10, data0['ladder_rank'])
        self.assertEqual(Version.WOL, data0['version'])

        data1 = data[1]

        self.assertEqual(r2.id, data1['id'])
        self.assertEqual(11, data1['ladder_rank'])
        self.assertEqual(Version.HOTS, data1['version'])

        data2 = data[2]

        self.assertEqual(r3.id, data2['id'])
        self.assertEqual(12, data2['ladder_rank'])
        self.assertEqual(Version.HOTS, data2['version'])

        data3 = data[3]

        self.assertEqual(r4.id, data3['id'])
        self.assertEqual(13, data3['ladder_rank'])
        self.assertEqual(Version.LOTV, data3['version'])

    def test_no_mmr_is_filtered_after_mmr_season(self):
        s27 = self.db.create_season(id=27)
        s28 = self.db.create_season(id=28)

        p1 = self.db.create_player(name="arne")
        t1 = self.db.create_team()

        r1 = self.db.create_ranking(season=s27)
        self.db.create_ranking_data(data=[dict(ladder_rank=10, mmr=NO_MMR)])

        r2 = self.db.create_ranking(season=s28)
        self.db.create_ranking_data(data=[dict(ladder_rank=11, mmr=NO_MMR)])

        r3 = self.db.create_ranking(season=s28)
        self.db.create_ranking_data(data=[dict(ladder_rank=12, mmr=120)])

        response = self.c.get('/team/%d/rankings/' % t1.id)

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(2, len(data))

        data0 = data[0]

        self.assertEqual(r1.id, data0['id'])
        self.assertEqual(10, data0['ladder_rank'])

        data1 = data[1]

        self.assertEqual(r3.id, data1['id'])
        self.assertEqual(12, data1['ladder_rank'])
        self.assertEqual(120, data1['mmr'])
