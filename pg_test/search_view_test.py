import json
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
        self.db.create_cache()
        self.db.create_season()
        self.db.create_ranking()

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Cache, Season, Ranking])
        self.c = Client()

    def test_search_by_name(self):
        p = self.db.create_player(name="arne")

        response = self.c.get('/search/', {'name': 'arne'})

        self.assertEqual(200, response.status_code)
        self.assertEqual([p], response.context['items'])
        self.assertIsNone(response.context['prev'])
        self.assertIsNone(response.context['next'])

    def test_search_by_name_prefix(self):
        p = self.db.create_player(name="sunexxxyz")

        response = self.c.get('/search/', {'name': 'sune'})

        self.assertEqual(200, response.status_code)
        self.assertEqual([p], response.context['items'])
        self.assertIsNone(response.context['prev'])
        self.assertIsNone(response.context['next'])

    def test_search_not_long_enough(self):
        response = self.c.get('/search/', {'name': 'n'})

        self.assertEqual(200, response.status_code)
        self.assertEqual(True, response.context['no_search'])

    def test_search_by_url(self):
        p = self.db.create_player(name="Kuno", bid=927, region=Region.EU, realm=1)
        p = self.db.create_player(name="Kuno", bid=927, region=Region.AM, realm=1)
        p = self.db.create_player(name="Kuno", bid=927, region=Region.KR, realm=1)
        p = self.db.create_player(name="Kuno", bid=927, region=Region.CN, realm=1)
        p = self.db.create_player(name="Kuno", bid=927, region=Region.SEA, realm=1)

        response = self.c.get('/search/', {'name': 'http://eu.battle.net/sc2/en/profile/927/1/Kuno/'})

        self.assertEqual(302, response.status_code)
        self.assertTrue('/player/' in response.url)

        response = self.c.get('/search/', {'name': 'http://us.battle.net/sc2/en/profile/927/1/Kuno/'})

        self.assertEqual(302, response.status_code)
        self.assertTrue('/player/' in response.url)

        response = self.c.get('/search/', {'name': 'http://kr.battle.net/sc2/en/profile/927/1/Kuno/'})

        self.assertEqual(302, response.status_code)
        self.assertTrue('/player/' in response.url)

        response = self.c.get('/search/', {'name': 'http://sea.battle.net/sc2/en/profile/927/1/Kuno/'})

        self.assertEqual(302, response.status_code)
        self.assertTrue('/player/' in response.url)

        response = self.c.get('/search/', {'name': 'http://www.battlenet.com.cn/sc2/en/profile/927/1/Kuno/'})

        self.assertEqual(302, response.status_code)
        self.assertTrue('/player/' in response.url)

    def test_pagination(self):
        for i in range(40):
            self.db.create_player(bid=300 + i, name='sune')

        response = self.c.get('/search/', {'name': 'sune'})

        self.assertEqual(200, response.status_code)
        self.assertEqual(32, len(response.context['items']))
        self.assertIsNone(response.context['prev'])
        self.assertEqual(32, response.context['next'])

        response = self.c.get('/search/', {'name': 'sune', 'offset': response.context['next']})

        self.assertEqual(200, response.status_code)
        self.assertEqual(8, len(response.context['items']))
        self.assertEqual(0, response.context['prev'])
        self.assertIsNone(response.context['next'])

    def test_json_api_search_by_name(self):
        p = self.db.create_player(bid=300, name='sune', race=Race.ZERG, league=League.GOLD, mode=Mode.TEAM_1V1)

        response = self.c.get('/search/', {'name': 'sune', 'json': ''})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(1, data['count'])
        self.assertEqual(0, data['offset'])
        self.assertEqual([
            {
                'name': 'sune',
                'tag': p.tag,
                'clan': p.clan,
                'race': 'zerg',
                'mode': '1v1',
                'bnet_url': 'http://eu.battle.net/sc2/en/profile/300/0/sune/',
                'region': 'eu',
                'league': 'gold',
                'season': self.db.season.id,
            }
        ], data['items'])

    def test_json_api_search_by_name_prefix_several_hits(self):
        p1 = self.db.create_player(bid=300, name='sune',
                                   race=Race.ZERG, league=League.GOLD, mode=Mode.TEAM_1V1)
        p2 = self.db.create_player(bid=301, name='sunebune',
                                   race=Race.TERRAN, league=League.PLATINUM, mode=Mode.ARCHON)
        p3 = self.db.create_player(bid=302, name='sunerune',
                                   race=Race.RANDOM, league=League.PLATINUM, mode=Mode.TEAM_1V1)

        response = self.c.get('/search/', {'name': 'sune', 'json': ''})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(3, data['count'])
        self.assertEqual(0, data['offset'])
        self.assertEqual([
            {
                'name': 'sune',
                'tag': p1.tag,
                'clan': p1.clan,
                'race': 'zerg',
                'mode': '1v1',
                'bnet_url': 'http://eu.battle.net/sc2/en/profile/300/0/sune/',
                'region': 'eu',
                'league': 'gold',
                'season': self.db.season.id,
            },
            {
                'name': 'sunerune',
                'tag': p3.tag,
                'clan': p3.clan,
                'race': 'random',
                'mode': '1v1',
                'bnet_url': 'http://eu.battle.net/sc2/en/profile/302/0/sunerune/',
                'region': 'eu',
                'league': 'platinum',
                'season': self.db.season.id,
            },
            {
                'name': 'sunebune',
                'tag': p2.tag,
                'clan': p2.clan,
                'race': 'terran',
                'mode': 'archon',
                'bnet_url': 'http://eu.battle.net/sc2/en/profile/301/0/sunebune/',
                'region': 'eu',
                'league': 'platinum',
                'season': self.db.season.id,
            },
        ], data['items'])

    def test_json_api_search_with_no_hits(self):
        p = self.db.create_player(bid=300, name='sune')

        response = self.c.get('/search/', {'name': 'kuno', 'json': ''})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(0, data['count'])
        self.assertEqual(0, data['offset'])
        self.assertEqual([], data['items'])

    def test_json_api_search_with_no_search(self):
        p = self.db.create_player(bid=300, name='sune')

        response = self.c.get('/search/', {'name': 'k', 'json': ''})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(-1, data['count'])

    def test_json_api_search_by_prefix_and_offset(self):
        p1 = self.db.create_player(bid=300, name='sune',
                                   race=Race.ZERG, league=League.GOLD, mode=Mode.TEAM_1V1)
        p2 = self.db.create_player(bid=301, name='sunebune',
                                   race=Race.TERRAN, league=League.PLATINUM, mode=Mode.ARCHON)
        p3 = self.db.create_player(bid=302, name='sunerune',
                                   race=Race.RANDOM, league=League.PLATINUM, mode=Mode.TEAM_1V1)

        response = self.c.get('/search/', {'name': 'sune', 'json': '', 'offset': '2'})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(3, data['count'])
        self.assertEqual(2, data['offset'])
        self.assertEqual([
            {
                'name': 'sunebune',
                'tag': p2.tag,
                'clan': p2.clan,
                'race': 'terran',
                'mode': 'archon',
                'bnet_url': 'http://eu.battle.net/sc2/en/profile/301/0/sunebune/',
                'region': 'eu',
                'league': 'platinum',
                'season': self.db.season.id,
            },
        ], data['items'])

    def test_json_api_search_by_prefix_and_offset_out_of_range(self):
        p = self.db.create_player(bid=300, name='sune', race=Race.ZERG, league=League.GOLD, mode=Mode.TEAM_1V1)

        response = self.c.get('/search/', {'name': 'sune', 'json': '', 'offset': '200'})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(1, data['count'])
        self.assertEqual(200, data['offset'])
        self.assertEqual([], data['items'])

        response = self.c.get('/search/', {'name': 'sune', 'json': '', 'offset': '-1'})

        self.assertEqual(200, response.status_code)

        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(1, data['count'])
        self.assertEqual(0, data['offset'])
        self.assertEqual([{
            'name': 'sune',
            'tag': p.tag,
            'clan': p.clan,
            'race': 'zerg',
            'mode': '1v1',
            'bnet_url': 'http://eu.battle.net/sc2/en/profile/300/0/sune/',
            'region': 'eu',
            'league': 'gold',
            'season': self.db.season.id,
        }], data['items'])
        
