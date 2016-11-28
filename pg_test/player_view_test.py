import aid.test.init_django_postgresql

from aid.test.db import Db

from aid.test.base import DjangoTestCase

from django.test import Client
from main.models import Mode, Season, Ranking, Cache
from django.core.cache import cache


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db.create_cache()
        self.s1 = self.db.create_season(id=16)
        self.s2 = self.db.create_season(id=17)
        self.db.create_ranking()

    def setUp(self):
        super().setUp()
        cache.clear()
        self.db.delete_all(keep=[Season, Cache, Ranking])
        self.c = Client()

    def test_view_player(self):
        p = self.db.create_player(name="arne")
        t = self.db.create_team(season=self.s2)

        response = self.c.get('/player/%d/' % p.id)

        self.assertEqual(200, response.status_code)
        self.assertEqual(p, response.context['player'])
        teams = response.context['teams']
        self.assertEqual([t.id], [t.id for t in teams])
        self.assertEqual('/ladder/hots/1v1/ladder-rank/?team=%d' % t.id, teams[0].ladder_url)

    def test_view_player_many_teams(self):
        p0 = self.db.create_player(name="arne0", bid=301)
        p1 = self.db.create_player(name="arne1", bid=302)
        p1 = self.db.create_player(name="arne2", bid=303)
        p2 = self.db.create_player(name="arne3", bid=304)
        p3 = self.db.create_player(name="arne4", bid=305)
        p4 = self.db.create_player(name="arne5", bid=306)
        t0 = self.db.create_team(mode=Mode.TEAM_1V1, season=self.s1, member0=p0)
        t1 = self.db.create_team(mode=Mode.TEAM_4V4, season=self.s1, member0=p3, member1=p2, member2=p1, member3=p0)
        t2 = self.db.create_team(mode=Mode.TEAM_2V2, season=self.s1, member0=p0, member1=p4)
        t3 = self.db.create_team(mode=Mode.ARCHON, season=self.s1, member0=p0, member1=p1)

        response = self.c.get('/player/%d/' % p0.id)

        self.assertEqual(200, response.status_code)
        self.assertEqual(p0, response.context['player'])
        teams = response.context['teams']
        self.assertEqual([t0.id, t3.id, t2.id, t1.id], [t.id for t in teams])
        self.assertEqual([False, False, False, False], [hasattr(t, 'ladder_url') for t in teams])
