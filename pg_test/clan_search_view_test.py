import json
from pprint import pprint

import aid.test.init_django_postgresql

from aid.test.db import Db

from aid.test.base import DjangoTestCase

from django.test import Client
from main.models import Region, Player, Cache, Season, Ranking, Race, Mode, League


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db.create_season(end_date=None)
        self.db.create_player(tag='TA', clan='Alfa')
        self.db.create_player(tag='TA', clan='Alfa')
        self.db.create_player(tag='TA', clan='Alfa')
        self.db.create_player(tag='TB', clan='YBeta')
        self.db.create_player(tag='TB', clan='YBeta')
        self.db.create_player(tag='XC', clan='YCure')

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Cache, Season, Ranking, Player])
        self.c = Client()

    def test_view_largest_teams(self):
        response = self.c.get('/clan/')
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                dict(tag='TA', clan='Alfa', count=3),
                dict(tag='TB', clan='YBeta', count=2),
                dict(tag='XC', clan='YCure', count=1),
            ],
            response.context['clans'])

    def test_search_hit_by_exact_name_redirects_to_clan_view(self):
        response = self.c.get('/clan/', {'clan': 'alfa'})
        self.assertEqual(302, response.status_code)
        self.assertEqual('/clan/TA/mmr/', response.url)

    def test_search_hit_by_exact_tag_redirects_to_clan_view(self):
        response = self.c.get('/clan/', {'clan': 'xc'})
        self.assertEqual(302, response.status_code)
        self.assertEqual('/clan/XC/mmr/', response.url)

    def test_search_hit_by_name_prefix_list_matches(self):
        response = self.c.get('/clan/', {'clan': 'y'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                dict(tag='TB', clan='YBeta', count=2),
                dict(tag='XC', clan='YCure', count=1),
            ],
            response.context['clans'])

    def test_search_hit_by_clan_prefix_list_matches(self):
        response = self.c.get('/clan/', {'clan': 't'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                dict(tag='TA', clan='Alfa', count=3),
                dict(tag='TB', clan='YBeta', count=2),
            ],
            response.context['clans'])

    def test_search_does_not_match_anything(self):
        response = self.c.get('/clan/', {'clan': 'nomatch'})
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.context['clans'])

