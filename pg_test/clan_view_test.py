import aid.test.init_django_postgresql

import json
import main.views.clan

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from django.test import Client

from common.utils import utcnow
from main.models import Version, League, Mode, Region, Race, Season, Cache, Ladder
from main.views.base import rankings_view_client
from django.conf import settings
from django.core.cache import cache
from lib import sc2


class TestClient(main.client.Client):
    """ Test client that does not request the server but calls the c++ directly. """

    def request_server(self, data):
        raw = sc2.direct_ladder_handler_request_clan(settings.DATABASES['default']['NAME'], json.dumps(data))
        return json.loads(raw)


# Replace client with test client that calls c++ handler directly.
main.views.clan.client = TestClient()


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.now = utcnow()
        self.today = self.now.date()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.s15 = self.db.create_season(id=15, start_date=self.date(days=-200), end_date=self.date(days=-101))
        self.s16 = self.db.create_season(id=16, start_date=self.date(days=-100), end_date=None)

    def setUp(self):
        super().setUp()
        cache.clear()
        self.db.clear_defaults()
        self.db.delete_all(keep=[Season, Cache, Ladder])
        self.c = Client()

    def tearDown(self):
        rankings_view_client.close()
        super(Test, self).tearDown()

    def test_simple_gets_with_various_filtering_and_sorting(self):

        p1 = self.db.create_player(tag='TL', clan='Team Liquid')
        p2 = self.db.create_player(tag='TL', clan='Team Liquid')

        t1 = self.db.create_team(member0=p1)
        t2 = self.db.create_team(member0=p2)

        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=t1.id, league=League.GOLD,     region=Region.EU, race0=Race.TERRAN, points=20, mmr=3,
                 version=Version.LOTV, wins=100, losses=100),
            dict(team_id=t2.id, league=League.PLATINUM, region=Region.AM, race0=Race.ZERG,   points=40, mmr=4,
                 version=Version.LOTV, wins=200, losses=200),
        ])

        def get_and_check(url, *players):
            response = self.c.get(url)
            self.assertEqual(200, response.status_code)
            teams = response.context['ladder']['teams']
            self.assertEqual(len(players), len(teams))
            for i, p in enumerate(players):
                self.assertEqual(p.name, teams[i]['m0_name'])

        get_and_check('/clan/TL/mmr/',           p2, p1)
        get_and_check('/clan/TL/-played/',       p1, p2)
        get_and_check('/clan/TL/wins/',          p2, p1)
        get_and_check('/clan/TL/league-points/', p2, p1)

        get_and_check('/clan/TL/mmr/?f=terran',   p1)
        get_and_check('/clan/TL/mmr/?f=am',       p2)
        get_and_check('/clan/TL/mmr/?f=eu,zerg')

    def test_other_clan_season_mode_version_are_excluded(self):

        trs = []

        p = self.db.create_player(tag='TL', clan='Team Liquid', season=self.s16, mode=Mode.TEAM_1V1)
        t = self.db.create_team(member0=p, mode=p.mode, season=p.season, version=Version.LOTV)
        trs.append(dict(team_id=t.id, mode=t.mode, version=t.version))
        p1 = p

        p = self.db.create_player(tag='XX', clan='Team Liquid', season=self.s16, mode=Mode.TEAM_1V1)
        t = self.db.create_team(member0=p, mode=p.mode, season=p.season, version=Version.LOTV)
        trs.append(dict(team_id=t.id, mode=t.mode, version=t.version))

        p = self.db.create_player(tag='TL', clan='Team Liquid', season=self.s15, mode=Mode.TEAM_1V1)
        t = self.db.create_team(member0=p, mode=p.mode, season=p.season, version=Version.LOTV)
        trs.append(dict(team_id=t.id, mode=t.mode, version=t.version))

        p = self.db.create_player(tag='TL', clan='Team Liquid', season=self.s16, mode=Mode.RANDOM_2V2)
        t = self.db.create_team(member0=p, mode=p.mode, season=p.season, version=Version.LOTV)
        trs.append(dict(team_id=t.id, mode=t.mode, version=t.version))

        p = self.db.create_player(tag='TL', clan='Team Liquid', season=self.s16, mode=Mode.TEAM_1V1)
        t = self.db.create_team(member0=p, mode=p.mode, season=p.season, version=Version.HOTS)
        trs.append(dict(team_id=t.id, mode=t.mode, version=t.version))

        self.db.create_ranking()
        self.db.create_ranking_data(data=trs)

        response = self.c.get('/clan/TL/mmr/')
        self.assertEqual(200, response.status_code)
        teams = response.context['ladder']['teams']
        self.assertEqual(1, len(teams))
        self.assertEqual(p1.name, teams[0]['m0_name'])

    def test_json_get(self):

        self.maxDiff = 1e9

        p1 = self.db.create_player(tag='TL')
        p2 = self.db.create_player(tag='TL')

        t1 = self.db.create_team(member0=p1)
        t2 = self.db.create_team(member0=p2)

        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=t1.id, league=League.PLATINUM, region=Region.EU, race0=Race.TERRAN, points=20,
                 version=Version.LOTV, wins=100, losses=100, mmr=3000),
            dict(team_id=t2.id, league=League.GOLD, region=Region.AM, race0=Race.ZERG,   points=40,
                 version=Version.LOTV, wins=200, losses=200, mmr=2000),
        ])

        response = self.c.get('/clan/TL/mmr/?json')
        self.assertEqual(200, response.status_code)
        teams = json.loads(response.content.decode('utf-8'))
        self.assertTrue(teams[0].pop("age"))
        self.assertTrue(teams[0].pop("data_time"))
        self.assertTrue(teams[1].pop("age"))
        self.assertTrue(teams[1].pop("data_time"))
        self.assertEqual([
            dict(
                rank=1,
                team_id=t1.id,
                league="platinum",
                tier=0,
                region="eu",
                m0_race="terran",
                m0_name=p1.name,
                m0_bnet_url=f'https://starcraft2.com/en-gb/profile/2/1/{p1.bid}',
                mmr=3000,
                win_rate=50.0,
                wins=100,
                losses=100,
                points=20.0,
            ),
            dict(
                rank=2,
                team_id=t2.id,
                league="gold",
                tier=0,
                region="am",
                m0_race="zerg",
                m0_name=p2.name,
                m0_bnet_url=f'https://starcraft2.com/en-gb/profile/2/1/{p2.bid}',
                mmr=2000,
                win_rate=50.0,
                wins=200,
                losses=200,
                points=40.0,
            ),
        ],
            teams)

