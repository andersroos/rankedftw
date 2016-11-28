import aid.test.init_django_sqlite

import json

from django.utils.datastructures import MultiValueDict
from aid.test.db import Db, Region
from aid.test.base import DjangoTestCase
from django.test import Client
from main.models import Mode, Season


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db.create_season(id=16)

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Season])
        self.c = Client()

    def test_get_1v1(self):
        p = self.db.create_player(region=Region.EU, realm=1, bid=301)
        t = self.db.create_team(mode=Mode.TEAM_1V1)

        response = self.c.get('/team/id/', {'mode': '1v1', 'player': 'http://eu.battle.net/sc2/en/profile/301/1/xyz'})

        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(t.id, data['team_id'])

    def test_get_4v4(self):
        p1 = self.db.create_player(region=Region.EU, realm=1, bid=301)
        p2 = self.db.create_player(region=Region.EU, realm=1, bid=302)
        p3 = self.db.create_player(region=Region.EU, realm=1, bid=303)
        p4 = self.db.create_player(region=Region.EU, realm=1, bid=304)
        t = self.db.create_team(mode=Mode.TEAM_4V4, member0=p1, member1=p2, member2=p3, member3=p4)

        qp = MultiValueDict()
        qp.setlist('player',
                   [
                       'http://eu.battle.net/sc2/en/profile/304/1/xyz',
                       'http://eu.battle.net/sc2/en/profile/303/1/xyz',
                       'http://eu.battle.net/sc2/en/profile/302/1/xyz',
                       'http://eu.battle.net/sc2/en/profile/301/1/xyz',
                   ])
        qp['mode'] = 'team-4v4'
        response = self.c.get('/team/id/', qp)

        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(t.id, data['team_id'])

