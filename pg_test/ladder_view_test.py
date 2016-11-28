import aid.test.init_django_postgresql

import json
import main.client
import main.views.ladder

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from django.test import Client
from main.models import Player, Version, Team, League, Mode, Region, Race, Season, Cache, Ladder
from main.views.base import rankings_view_client
from django.conf import settings
from django.core.cache import cache
from random import shuffle
from lib import sc2


class TestClient(main.client.Client):
    """ Test client that does not request the server but calls the c++ directly. """

    def request_server(self, data):
        raw = sc2.direct_ladder_handler_request_ladder(settings.DATABASES['default']['NAME'], json.dumps(data))
        return json.loads(raw)


# Replace client with test client that calls c++ handler directly.
main.views.ladder.client = TestClient()


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

        # Required objects, not actually used in test cases.
        self.db.create_cache()
        self.db.create_ladder()

        self.db.create_season()
        self.teams = self.db.create_teams(count=20)
        for i, team in enumerate(self.teams):
            setattr(self, 't%d' % i, team)
            setattr(self, 't%d_i' % i, team.id)
            setattr(self, 't%d_m0_n' % i, team.member0.name)
            setattr(self, 't%d_m0_i' % i, team.member0.id)

    def setUp(self):
        super().setUp()
        cache.clear()
        self.db.clear_defaults()
        self.db.delete_all(keep=[Season, Cache, Ladder, Team, Player])
        self.c = Client()

        # Change page size for easier testing.
        main.views.ladder.PAGE_SIZE = 10

    def tearDown(self):
        rankings_view_client.close()
        super(Test, self).tearDown()

    def get_page(self, url, content=["rank", "team_id"], page_size=10):
        """ Get the page and per team on page return the data indexed by content arg. """
        main.views.ladder.PAGE_SIZE = page_size
        cache.clear()
        response = self.c.get(url)
        self.assertEqual(200, response.status_code)
        if len(content) == 1:
            return [t[content[0]] for t in response.context['ladder']['teams']]
        else:
            return [tuple(t[i] for i in content) for t in response.context['ladder']['teams']]

    def test_simple_ladder(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t0_i, league=League.GOLD,     mmr=30, tier=0),
            dict(team_id=self.t1_i, league=League.PLATINUM, mmr=60, tier=1),
            dict(team_id=self.t2_i, league=League.PLATINUM, mmr=50, tier=2),
        ])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/')
        self.assertEqual(200, response.status_code)

        self.assertEqual(1, response.context['team_size'])
        self.assertEqual(0, response.context['highlight_team_id'])
        self.assertEqual(3, response.context['ladder']['count'])
        self.assertEqual(0, response.context['ladder']['offset'])

        page = response.context['ladder']['teams']

        self.assertEqual(self.t1_m0_n, page[0]["m0_name"])
        self.assertEqual(self.t2_m0_n, page[1]["m0_name"])
        self.assertEqual(self.t0_m0_n, page[2]["m0_name"])

    def test_two_players_with_the_same_mmr_should_get_same_rank(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[
            dict(team_id=self.t0_i, league=League.PLATINUM, mmr=50),
            dict(team_id=self.t1_i, league=League.PLATINUM, mmr=50),
            dict(team_id=self.t2_i, league=League.GOLD,     mmr=20),
            dict(team_id=self.t3_i, league=League.GOLD,     mmr=20),
        ])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/')
        self.assertEqual(200, response.status_code)

        page = response.context['ladder']['teams']

        self.assertEqual(self.t0_m0_n, page[0]["m0_name"])
        self.assertEqual(self.t1_m0_n, page[1]["m0_name"])
        self.assertEqual(self.t2_m0_n, page[2]["m0_name"])
        self.assertEqual(self.t3_m0_n, page[3]["m0_name"])

        self.assertEqual(1, page[0]["rank"])
        self.assertEqual(1, page[1]["rank"])
        self.assertEqual(3, page[2]["rank"])
        self.assertEqual(3, page[3]["rank"])

    def test_10_players_get_the_same_rank_works_over_pages(self):
        teams = self.teams
        data = [dict(team_id=teams[0].id, mmr=200)]
        for i in range(1, 11):
            data.append(dict(team_id=teams[i].id, mmr=199))
        for i in range(11, 20):
            data.append(dict(team_id=teams[i].id, mmr=188))
        self.db.create_ranking()
        self.db.create_ranking_data(data=data)

        response = self.c.get('/ladder/hots/1v1/ladder-rank/')
        self.assertEqual(200, response.status_code)

        page = response.context['ladder']['teams']

        # Check that the entire first page is just 1, 2, 2, .., 2

        self.assertEqual(self.t0_m0_n, page[0]["m0_name"])
        self.assertEqual(1, page[0]["rank"])

        self.assertEqual(self.t1_m0_n, page[1]["m0_name"])
        self.assertEqual(2, page[1]["rank"])

        self.assertEqual(self.t9_m0_n, page[-1]["m0_name"])
        self.assertEqual(2, page[-1]["rank"])

        # For offset 1 team 1-10 should all have rank 2.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=1')
        self.assertEqual(200, response.status_code)

        page = response.context['ladder']['teams']

        self.assertEqual(self.t1_m0_n, page[0]["m0_name"])
        self.assertEqual(2, page[0]["rank"])

        self.assertEqual(self.t10_m0_n, page[-1]["m0_name"])
        self.assertEqual(2, page[-1]["rank"])

        # For offset 6 team 1-5 should have rank 2 and team 6-10 should have rank 12.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=6')
        self.assertEqual(200, response.status_code)

        page = response.context['ladder']['teams']

        self.assertEqual(self.t6_m0_n, page[0]["m0_name"])
        self.assertEqual(2, page[0]["rank"])

        self.assertEqual(2, page[4]["rank"])

        self.assertEqual(12, page[5]["rank"])

        self.assertEqual(self.t15_m0_n, page[-1]["m0_name"])
        self.assertEqual(12, page[-1]["rank"])

    def test_ladder_rank_sorting_sorts_on__ladder_rank__wins__losses__team_id__also_test_filters(self):
        self.db.default_ranking_data__data = dict(
            version=Version.HOTS,
            race0=Race.ZERG,
            region=Region.EU,
        )
        self.db.create_ranking()
        data = [
            # Outside all filters.
            dict(team_id=self.t11_i, league=League.PLATINUM, mmr=3000, version=Version.WOL),
            dict(team_id=self.t12_i, league=League.PLATINUM, mmr=3000, mode=Mode.RANDOM_2V2),
            # Inside most filters.
            dict(team_id=self.t0_i,  league=League.BRONZE, mmr=0, wins=0, losses=2, race0=Race.TERRAN),
            dict(team_id=self.t1_i,  league=League.BRONZE, mmr=0, wins=0, losses=2, region=Region.AM),
            dict(team_id=self.t2_i,  league=League.BRONZE, mmr=0, wins=0, losses=1),
            dict(team_id=self.t3_i,  league=League.BRONZE, mmr=0, wins=1, losses=1),
            dict(team_id=self.t4_i,  league=League.BRONZE, mmr=1, wins=1, losses=1),
            dict(team_id=self.t5_i,  league=League.SILVER, mmr=1000, wins=0, losses=4),
            dict(team_id=self.t6_i,  league=League.GOLD, mmr=2000, wins=0, losses=4),
            dict(team_id=self.t7_i,  league=League.PLATINUM, mmr=3000, wins=0, losses=4),
            dict(team_id=self.t8_i,  league=League.DIAMOND, mmr=4000, wins=0, losses=4),
            dict(team_id=self.t9_i,  league=League.MASTER, mmr=5000, wins=0, losses=4),
            dict(team_id=self.t10_i, league=League.GRANDMASTER, mmr=6000, wins=0, losses=4),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        #
        # Test default filtering, (0 is before 1 because lower team_id is before).
        #

        self.assertEqual([
            (1, self.t10_i),
            (2, self.t9_i),
            (3, self.t8_i),
            (4, self.t7_i),
            (5, self.t6_i),
            (6, self.t5_i),
            (7, self.t4_i),
            (8, self.t3_i),
            (8, self.t2_i),
            (8, self.t0_i),
            (8, self.t1_i)
        ], self.get_page('/ladder/hots/1v1/ladder-rank/', page_size=20))

        self.assertEqual([
            (1,  self.t1_i),
            (1,  self.t0_i),
            (1,  self.t2_i),
            (1,  self.t3_i),
            (5,  self.t4_i),
            (6,  self.t5_i),
            (7,  self.t6_i),
            (8,  self.t7_i),
            (9,  self.t8_i),
            (10, self.t9_i),
            (11, self.t10_i),
        ], self.get_page('/ladder/hots/1v1/-ladder-rank/', page_size=20))

        #
        # Test another version filtering.
        #

        self.assertEqual([(1, self.t11_i)], self.get_page('/ladder/wol/1v1/ladder-rank/'))
        self.assertEqual([(1, self.t11_i)], self.get_page('/ladder/wol/1v1/-ladder-rank/'))

        #
        # Test another mode version filtering.
        #

        self.assertEqual([(1, self.t12_i)], self.get_page('/ladder/hots/random-2v2/ladder-rank/'))
        self.assertEqual([(1, self.t12_i)], self.get_page('/ladder/hots/random-2v2/-ladder-rank/'))

        #
        # Test league filtering.
        #

        expected_order = []
        self.assertEqual([
            (1, self.t4_i),
            (2, self.t3_i),
            (2, self.t2_i),
            (2, self.t0_i),
            (2, self.t1_i),
        ], self.get_page('/ladder/hots/1v1/ladder-rank/?f=bronze'))

        self.assertEqual([
            (1, self.t1_i),
            (1, self.t0_i),
            (1, self.t2_i),
            (1, self.t3_i),
            (5, self.t4_i),
        ], self.get_page('/ladder/hots/1v1/-ladder-rank/?f=bronze'))

        #
        # Test race filtering.
        #

        self.assertEqual([(1, self.t0_i)], self.get_page('/ladder/hots/1v1/ladder-rank/?f=terran'))
        self.assertEqual([(1, self.t0_i)], self.get_page('/ladder/hots/1v1/-ladder-rank/?f=terran'))

        #
        # Test region filtering.
        #

        self.assertEqual([(1, self.t1_i)], self.get_page('/ladder/hots/1v1/ladder-rank/?f=am'))
        self.assertEqual([(1, self.t1_i)], self.get_page('/ladder/hots/1v1/-ladder-rank/?f=am'))

        #
        # Test league, region and race filtering.
        #

        self.assertEqual([
            (1, self.t4_i),
            (2, self.t3_i),
            (2, self.t2_i),
        ], self.get_page('/ladder/hots/1v1/ladder-rank/?f=bronze,zerg,eu'))

        self.assertEqual([
            (1, self.t2_i),
            (1, self.t3_i),
            (3, self.t4_i),
        ], self.get_page('/ladder/hots/1v1/-ladder-rank/?f=bronze,zerg,eu'))

    def test_games_played_sorts_on__played__mmr__wins__team_id(self):
        self.db.create_ranking()
        data = [
            dict(team_id=self.t0_i, league=League.SILVER,  mmr=2, wins=9, losses=9, points=2),
            dict(team_id=self.t1_i, league=League.DIAMOND, mmr=2, wins=9, losses=8, points=1),
            dict(team_id=self.t2_i, league=League.BRONZE,  mmr=1, wins=9, losses=8, points=9),
            dict(team_id=self.t3_i, league=League.GOLD,    mmr=1, wins=8, losses=9, points=8),
            dict(team_id=self.t4_i, league=League.DIAMOND, mmr=1, wins=8, losses=9, points=7),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        self.assertEqual([
            (1, self.t0_i),
            (2, self.t1_i),
            (2, self.t2_i),
            (2, self.t3_i),
            (2, self.t4_i),
        ], self.get_page('/ladder/hots/1v1/played/'))

        self.assertEqual([
            (1, self.t4_i),
            (1, self.t3_i),
            (1, self.t2_i),
            (1, self.t1_i),
            (5, self.t0_i),
        ], self.get_page('/ladder/hots/1v1/-played/'))

    def test_wins_sorts_on__wins__mmr__losses__team_id(self):
        self.db.create_ranking()
        data = [
            dict(team_id=self.t0_i, league=League.SILVER,  mmr=1, wins=9, losses=8, points=2),
            dict(team_id=self.t1_i, league=League.SILVER,  mmr=0, wins=9, losses=8, points=5),
            dict(team_id=self.t2_i, league=League.DIAMOND, mmr=0, wins=9, losses=9, points=6),
            dict(team_id=self.t3_i, league=League.BRONZE,  mmr=0, wins=8, losses=9, points=3),
            dict(team_id=self.t4_i, league=League.GOLD,    mmr=0, wins=8, losses=9, points=7),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        self.assertEqual([
            (1, self.t0_i),
            (1, self.t1_i),
            (1, self.t2_i),
            (4, self.t3_i),
            (4, self.t4_i),
        ], self.get_page('/ladder/hots/1v1/wins/'))
                        
        self.assertEqual([
            (1, self.t4_i),
            (1, self.t3_i),
            (3, self.t2_i),
            (3, self.t1_i),
            (3, self.t0_i),
        ], self.get_page('/ladder/hots/1v1/-wins/'))

    def test_losses_sorts_on__losses__wins__team_id(self):
        self.db.create_ranking()
        data = [
            dict(team_id=self.t0_i, league=League.SILVER,  mmr=0, wins=8, losses=9),
            dict(team_id=self.t1_i, league=League.SILVER,  mmr=0, wins=9, losses=9),
            dict(team_id=self.t2_i, league=League.DIAMOND, mmr=0, wins=9, losses=8),
            dict(team_id=self.t3_i, league=League.BRONZE,  mmr=0, wins=9, losses=8),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        self.assertEqual([
            (1, self.t0_i),
            (1, self.t1_i),
            (3, self.t2_i),
            (3, self.t3_i),
        ], self.get_page('/ladder/hots/1v1/losses/'))

        self.assertEqual([
            (1, self.t3_i),
            (1, self.t2_i),
            (3, self.t1_i),
            (3, self.t0_i),
        ], self.get_page('/ladder/hots/1v1/-losses/'))

    def test_win_rate_sorts_om__win_rate__played__mmr__team_id(self):
        self.db.create_ranking()
        data = [
            dict(team_id=self.t0_i, league=League.SILVER,  mmr=2, wins=9, losses=1),
            dict(team_id=self.t1_i, league=League.SILVER,  mmr=2, wins=5, losses=5),
            dict(team_id=self.t2_i, league=League.SILVER,  mmr=4, wins=4, losses=4),
            dict(team_id=self.t3_i, league=League.DIAMOND, mmr=4, wins=4, losses=4),
            dict(team_id=self.t4_i, league=League.BRONZE,  mmr=4, wins=4, losses=4),
            dict(team_id=self.t5_i, league=League.BRONZE,  mmr=4, wins=4, losses=7),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        self.assertEqual([
            (1, self.t0_i),
            (2, self.t1_i),
            (2, self.t2_i),
            (2, self.t3_i),
            (2, self.t4_i),
            (6, self.t5_i),
        ], self.get_page('/ladder/hots/1v1/win-rate/'))

        self.assertEqual([
            (1, self.t5_i),
            (2, self.t4_i),
            (2, self.t3_i),
            (2, self.t2_i),
            (2, self.t1_i),
            (6, self.t0_i),
        ], self.get_page('/ladder/hots/1v1/-win-rate/'))

    def test_pagination_with_no_gap_between_start_and_end_section(self):
        self.db.create_ranking()
        data = [dict(team_id=team.id) for team in self.teams]
        self.db.create_ranking_data(data=data)

        main.views.ladder.PAGE_SIZE = 3  # => 7 sections

        response = self.c.get('/ladder/hots/1v1/ladder-rank/')

        pages = response.context['pages']

        self.assertEqual(0, response.context['current_page'])
        self.assertEqual(7, len(pages))
        self.assertEqual(0, len([p for p in pages if 'gap' in p]))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/', index=0),           pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=18', index=6), pages[6])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=18')

        pages = response.context['pages']

        self.assertEqual(6, response.context['current_page'])
        self.assertEqual(7, len(pages))
        self.assertEqual(0, len([p for p in pages if 'gap' in p]))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/', index=0),           pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=18', index=6), pages[6])

    def test_pagination_with_start_middle_and_end_section(self):
        self.db.create_ranking()
        data = [dict(team_id=team.id) for team in self.teams]
        self.db.create_ranking_data(data=data)

        main.views.ladder.PAGE_SIZE = 1  # => 20 sections, index and offset are the same.

        # Test last page with connecting start and middle section.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=7')

        pages = response.context['pages']

        self.assertEqual(7, response.context['current_page'])
        self.assertEqual(11 + 1 + 4, len(pages))
        self.assertEqual(1, len([p for p in pages if 'gap' in p]))

        self.assertEqual(0,  pages[0]['index'])
        self.assertEqual(10, pages[10]['index'])
        self.assertIn('gap', pages[11])
        self.assertEqual(16, pages[12]['index'])
        self.assertEqual(19, pages[15]['index'])

        # Test first page with separate start and middle section.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=8')

        pages = response.context['pages']

        self.assertEqual(8, response.context['current_page'])
        self.assertEqual(4 + 1 + 7 + 1 + 4, len(pages))
        self.assertEqual(2, len([p for p in pages if 'gap' in p]))

        self.assertEqual(0,  pages[0]['index'])
        self.assertEqual(3,  pages[3]['index'])
        self.assertIn('gap', pages[4])
        self.assertEqual(5,  pages[5]['index'])
        self.assertEqual(11, pages[11]['index'])
        self.assertIn('gap', pages[12])
        self.assertEqual(16, pages[13]['index'])
        self.assertEqual(19, pages[16]['index'])

        # Test last page with separate middle and end section.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=11')

        pages = response.context['pages']

        self.assertEqual(11, response.context['current_page'])
        self.assertEqual(4 + 1 + 7 + 1 + 4, len(pages))
        self.assertEqual(2, len([p for p in pages if 'gap' in p]))

        self.assertEqual(0,  pages[0]['index'])
        self.assertEqual(3,  pages[3]['index'])
        self.assertIn('gap', pages[4])
        self.assertEqual(8,  pages[5]['index'])
        self.assertEqual(14, pages[11]['index'])
        self.assertIn('gap', pages[12])
        self.assertEqual(16, pages[13]['index'])
        self.assertEqual(19, pages[16]['index'])

        # Test first page with connecting middle and end section.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=12')

        pages = response.context['pages']

        self.assertEqual(12, response.context['current_page'])
        self.assertEqual(4 + 1 + 11, len(pages))
        self.assertEqual(1, len([p for p in pages if 'gap' in p]))

        self.assertEqual(0,  pages[0]['index'])
        self.assertEqual(3,  pages[3]['index'])
        self.assertIn('gap', pages[4])
        self.assertEqual(9,  pages[5]['index'])
        self.assertEqual(19, pages[15]['index'])

    def test_non_aligned_pagination(self):
        self.db.create_ranking()
        data = [dict(team_id=team.id) for team in self.teams]
        data.extend(dict(team_id=team.id, mode=Mode.TEAM_2V2) for team in self.teams)
        self.db.create_ranking_data(data=data)

        main.views.ladder.PAGE_SIZE = 5  # => 4 sections, all visible all the time.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=7')

        pages = response.context['pages']

        self.assertEqual(2, response.context['current_page'])
        self.assertEqual(5, len(pages))
        self.assertEqual(0, len([p for p in pages if 'gap' in p]))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/',           index=0), pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=2',  index=1), pages[1])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=7',  index=2), pages[2])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=12', index=3), pages[3])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=17', index=4), pages[4])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=19')

        pages = response.context['pages']
        page = response.context['ladder']['teams']

        self.assertEqual(4, response.context['current_page'])
        self.assertEqual(5, len(pages))
        self.assertEqual(0, len([p for p in pages if 'gap' in p]))
        self.assertEqual(1, len(page))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?offset=19', index=4), pages[4])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=21')

        pages = response.context['pages']
        page = response.context['ladder']['teams']

        self.assertEqual(-1, response.context['current_page'])
        self.assertEqual(4, len(pages))
        self.assertEqual(0, len([p for p in pages if 'gap' in p]))
        self.assertEqual(0, len(page))

    def test_pagination_start_offset_with_team_link(self):
        self.db.create_ranking()
        data = [dict(team_id=team.id) for team in self.teams]
        self.db.create_ranking_data(data=data)

        main.views.ladder.PAGE_SIZE = 12  # team link wants to display -10 iteams.

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?team=%d' % self.t14_i)

        pages = response.context['pages']
        page = response.context['ladder']['teams']

        self.assertEqual(1, response.context['current_page'])
        self.assertEqual(3, len(pages))

        self.assertEqual(self.t14_i, page[10]["team_id"])
        self.assertEqual(12, len(page))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?team=%d&offset=0' % self.t14_i,  index=0), pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?team=%d&offset=4' % self.t14_i,  index=1), pages[1])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?team=%d&offset=16' % self.t14_i, index=2), pages[2])

    def test_team_link_with_and_without_filtering(self):
        self.db.create_ranking()
        data = [dict(team_id=team.id, race0=(Race.ZERG if team.id % 2 == 1 else Race.TERRAN)) for team in self.teams]
        self.db.create_ranking_data(data=data)

        main.views.ladder.PAGE_SIZE = 8

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?f=zerg&team=%d' % self.t14_i)

        pages = response.context['pages']
        page = response.context['ladder']['teams']

        self.assertEqual(0, response.context['current_page'])
        self.assertEqual(2, len(pages))

        self.assertEqual(self.t14_i, page[7]["team_id"])
        self.assertEqual(8, len(page))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?f=zerg&team=%d&offset=0' % self.t14_i, index=0),
                         pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?f=zerg&team=%d&offset=8' % self.t14_i, index=1),
                         pages[1])

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?f=terran&team=%d' % self.t14_i)

        pages = response.context['pages']
        page = response.context['ladder']['teams']

        self.assertEqual(0, response.context['current_page'])
        self.assertEqual(2, len(pages))

        self.assertNotIn(self.t14_i, [p["team_id"] for p in page])
        self.assertEqual(8, len(page))

        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?f=terran&team=%d&offset=0' % self.t14_i, index=0),
                         pages[0])
        self.assertEqual(dict(href='/ladder/hots/1v1/ladder-rank/?f=terran&team=%d&offset=8' % self.t14_i, index=1),
                         pages[1])

    def test_various_bad_requests_for_good_code_coverage_and_error_checking(self):
        self.db.create_ranking()
        self.db.create_ranking_data(data=[dict(team_id=self.t1_i)])

        response = self.c.get('/ladder/bw/1v1/ladder-rank/')
        self.assertEqual(404, response.status_code)

        response = self.c.get('/ladder/hots/team-5v5/ladder-rank/')
        self.assertEqual(404, response.status_code)

        response = self.c.get('/ladder/hots/1v1/mmr/')
        self.assertEqual(404, response.status_code)

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?offset=%d' % 3e9)
        self.assertEqual(404, response.status_code)

        response = self.c.get('/ladder/hots/1v1/ladder-rank/?team=%d' % 3e9)
        self.assertEqual(404, response.status_code)

    def test_race_filtering_on_archon_mode_which_normally_does_not_work_on_teams(self):
        self.db.default_ranking_data__data = dict(
            version=Version.LOTV,
            mode=Mode.ARCHON,
        )

        t0 = self.db.create_team(
            mode=Mode.ARCHON, version=Version.LOTV,
            member0=self.db.create_player(), race0=Race.ZERG,
            member1=self.db.create_player(), race1=Race.ZERG,
        )

        t1 = self.db.create_team(
            mode=Mode.ARCHON, version=Version.LOTV,
            member0=self.db.create_player(), race0=Race.PROTOSS,
            member1=self.db.create_player(), race1=Race.PROTOSS,
        )

        t2 = self.db.create_team(
            mode=Mode.ARCHON, version=Version.LOTV,
            member0=self.db.create_player(), race0=Race.ZERG,
            member1=self.db.create_player(), race1=Race.ZERG,
        )

        t3 = self.db.create_team(
            mode=Mode.ARCHON, version=Version.LOTV,
            member0=self.db.create_player(), race0=Race.TERRAN,
            member1=self.db.create_player(), race1=Race.TERRAN,
        )

        self.db.create_ranking()
        data = [
            dict(team_id=t0.id, league=League.PLATINUM, mmr=50, race0=Race.ZERG, race1=Race.ZERG),
            dict(team_id=t1.id, league=League.PLATINUM, mmr=40, race0=Race.PROTOSS, race1=Race.PROTOSS),
            dict(team_id=t2.id, league=League.PLATINUM, mmr=30, race0=Race.ZERG, race1=Race.ZERG),
            dict(team_id=t3.id, league=League.PLATINUM, mmr=20, race0=Race.TERRAN, race1=Race.TERRAN),
        ]
        shuffle(data)
        self.db.create_ranking_data(data=data)

        #
        # Test default filtering.
        #

        self.assertEqual([
            (1, t0.id),
            (2, t1.id),
            (3, t2.id),
            (4, t3.id),
        ], self.get_page('/ladder/lotv/archon/ladder-rank/', page_size=20))

        #
        # Test race filtering.
        #

        self.assertEqual([(1, t0.id), (2, t2.id)], self.get_page('/ladder/lotv/archon/ladder-rank/?f=zerg'))
        self.assertEqual([(1, t1.id)], self.get_page('/ladder/lotv/archon/ladder-rank/?f=protoss'))
        self.assertEqual([(1, t3.id)], self.get_page('/ladder/lotv/archon/ladder-rank/?f=terran'))
        self.assertEqual([], self.get_page('/ladder/lotv/archon/ladder-rank/?f=random'))

