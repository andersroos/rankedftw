from copy import deepcopy

import aid.test.init_django_sqlite

from io import StringIO
from urllib.error import URLError
from unittest.mock import Mock
from aid.test.base import DjangoTestCase, MockBnetTestMixin
from common.utils import utcnow, from_unix
from main.battle_net import LocalStatus, ApiLadder, NO_MMR
from main.models import Region, Race
from test.api_data import API_LADDER_4V4, API_LADDER_1V1, LEGACY_API_LADDER_4V4, LEGACY_API_LADDER_1V1


class Res(object):

    def __init__(self, content):
        self.content = content

    @staticmethod
    def getcode():
        return 200

    def readall(self):
        return self.content


class Test(MockBnetTestMixin, DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.region = Region.EU

    def mock_response(self, content):
        self.bnet.raw_get = Mock(return_value=Res(content))

    def test_fetch_ladder_handles_none_response(self):
        self.bnet.raw_get = Mock(side_effect=URLError('Connection refused', StringIO('')))

        status, data = self.bnet.http_get_json('', 1, '')

        self.assertEqual(601, status)

    def test_http_get_json_handles_unparsable_json(self):
        self.mock_raw_get(status=605, content="!!¤#%&¤/&")

        status, data = self.bnet.http_get_json('', 1, '')

        self.assertEqual(LocalStatus.UNPARSABLE_JSON, status)
        self.assertEqual({'unparsable': "!!¤#%&¤/&"}, data)


class TestApi(DjangoTestCase):
    
    def test_parsing_of_1v1_ladder_works(self):
        al = ApiLadder(API_LADDER_1V1)
    
        self.assertEqual(from_unix(1479018088), al.first_join())
        self.assertEqual(from_unix(1479018088), al.last_join())
        self.assertEqual(1, al.member_count())
        self.assertEqual(381, al.max_points())
        self.assertEqual([{
            'join_time': 1479018088,
            'bid': 6205328,
            'realm': 1,
            'name': 'peimon',
            'tag': 'Partha',
            'clan': 'boom boom long time',
            'points': 381,
            'mmr': 2136,
            'wins': 12,
            'losses': 24,
            'race': Race.PROTOSS,
        }], al.members_for_ranking(1))

    def test_skips_empty_members(self):
        l = deepcopy(API_LADDER_1V1)
        del l['team'][0]['member']
        al = ApiLadder(l)

        self.assertEqual(from_unix(1479018088), al.first_join())
        self.assertEqual(from_unix(1479018088), al.last_join())
        self.assertEqual(0, al.member_count())
        self.assertEqual(381, al.max_points())
        self.assertEqual([], al.members_for_ranking(1))

    def test_skips_empty_member(self):
        l = deepcopy(API_LADDER_1V1)
        l['team'][0]['member'] = []
        al = ApiLadder(l)

        self.assertEqual(from_unix(1479018088), al.first_join())
        self.assertEqual(from_unix(1479018088), al.last_join())
        self.assertEqual(0, al.member_count())
        self.assertEqual(381, al.max_points())
        self.assertEqual([], al.members_for_ranking(1))

    def test_converts_high_mmr_as_no_mmr(self):
        l = deepcopy(API_LADDER_1V1)
        l['team'][0]['rating'] = 500342
        al = ApiLadder(l)
        self.assertEqual(NO_MMR, al.members_for_ranking(1)[0]['mmr'])

    def test_survives_missing_char(self):
        l = deepcopy(API_LADDER_1V1)
        del l['team'][0]['member'][0]['character_link']
        al = ApiLadder(l)
        self.assertEqual([{
            'join_time': 1479018088,
            'bid': 6205328,
            'realm': 1,
            'name': 'peimon',
            'tag': 'Partha',
            'clan': 'boom boom long time',
            'points': 381,
            'mmr': 2136,
            'wins': 12,
            'losses': 24,
            'race': Race.PROTOSS,
        }], al.members_for_ranking(1))

    def test_handles_empty(self):
        l = deepcopy(API_LADDER_1V1)
        del l['team']
        al = ApiLadder(l)
        self.assertEqual(None, al.first_join())
        self.assertEqual(None, al.last_join())
        self.assertEqual(0, al.member_count())
        self.assertEqual(None, al.max_points())
        self.assertEqual([], al.members_for_ranking(1))

    def test_parsing_of_4v4_ladder_works(self):
        al = ApiLadder(API_LADDER_4V4)

        self.assertEqual(from_unix(1479927625), al.first_join())
        self.assertEqual(from_unix(1479927625), al.last_join())
        self.assertEqual(4, al.member_count())
        self.assertEqual(0, al.max_points())
        self.assertEqual([
            {
                'join_time': 1479927625,
                'bid': 897866,
                'realm': 1,
                'name': 'AaxeoiS',
                'tag': '',
                'clan': '',
                'race': Race.TERRAN,
                'points': 0,
                'mmr': 3965,
                'wins': 4,
                'losses': 1,
            },
            {
                'join_time': 1479927625,
                'bid': 1048851,
                'realm': 1,
                'name': 'Hodn',
                'tag': '',
                'clan': '',
                'race': Race.RANDOM,
                'points': 0,
                'mmr': 3965,
                'wins': 4,
                'losses': 1,
            },
            {
                'join_time': 1479927625,
                'bid': 1371993,
                'realm': 1,
                'name': 'Tsakal',
                'tag': 'GROF',
                'clan': 'Greek Operation Forces',
                'race': Race.ZERG,
                'points': 0,
                'mmr': 3965,
                'wins': 4,
                'losses': 1,
            },
            {
                'join_time': 1479927625,
                'bid': 2972548,
                'realm': 1,
                'name': 'sakis',
                'tag': 'munaki',
                'clan': 'munaki',
                'race': Race.RANDOM,
                'points': 0,
                'mmr': 3965,
                'wins': 4,
                'losses': 1,
            }
        ], al.members_for_ranking(4))

    def test_parsing_of_1v1_legacy_ladder_works(self):
        al = ApiLadder(LEGACY_API_LADDER_1V1)

        self.assertEqual(from_unix(1468138637), al.first_join())
        self.assertEqual(from_unix(1468138637), al.last_join())
        self.assertEqual(1, al.member_count())
        self.assertEqual(101, al.max_points())
        self.assertEqual([
            {
                'join_time': 1468138637,
                'bid': 6061640,
                'realm': 1,
                'name': 'QueenOFpaiN',
                'tag': 'PIN',
                'clan': 'Pain',
                'race': Race.ZERG,
                'points': 101.0,
                'mmr': NO_MMR,
                'wins': 4,
                'losses': 1,
            }
        ], al.members_for_ranking(1))

    def test_parsing_of_4v4_legacy_ladder_works(self):
        al = ApiLadder(LEGACY_API_LADDER_4V4)

        self.assertEqual(from_unix(1478313972), al.first_join())
        self.assertEqual(from_unix(1478313972), al.last_join())
        self.assertEqual(4, al.member_count())
        self.assertEqual(0.0, al.max_points())
        self.assertEqual([
            {
                'join_time': 1478313972,
                'bid': 6539206,
                'realm': 1,
                'name': 'Maximus',
                'tag': '',
                'clan': '',
                'race': Race.PROTOSS,
                'points': 0.0,
                'mmr': NO_MMR,
                'wins': 0,
                'losses': 5,
            },
            {
                'join_time': 1478313972,
                'bid': 6714244,
                'realm': 1,
                'name': 'Herakles',
                'tag': '',
                'clan': '',
                'race': Race.TERRAN,
                'points': 0.0,
                'mmr': NO_MMR,
                'wins': 0,
                'losses': 5,
            },
            {
                'join_time': 1478313972,
                'bid': 6718054,
                'realm': 1,
                'name': 'Amazone',
                'tag': '',
                'clan': '',
                'race': Race.TERRAN,
                'points': 0.0,
                'mmr': NO_MMR,
                'wins': 0,
                'losses': 5,
            },
            {
                'join_time': 1478313972,
                'bid': 6742389,
                'realm': 1,
                'name': 'philipp',
                'tag': 'TAG',
                'clan': 'CLAN',
                'race': Race.ZERG,
                'points': 0.0,
                'mmr': NO_MMR,
                'wins': 0,
                'losses': 5,
            },
        ], al.members_for_ranking(4))




