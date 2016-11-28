from unittest.mock import Mock

import aid.test.init_django_sqlite

from aid.test.base import DjangoTestCase, MockBnetTestMixin
from common.utils import utcnow
from main.battle_net import ApiSeason, SeasonResponse
from main.fetch import fetch_new_in_league
from main.fetch_new import fetch_new
from main.models import Ladder
from main.models import Region, Season, Mode, League, Version


class Test(MockBnetTestMixin, DjangoTestCase):

    def setUp(self):
        super().setUp()
        self.db.delete_all()
        self.now = utcnow()
        self.today = self.now.date()
        self.s16 = self.db.create_season(id=16,
                                         start_date=self.date(days=-20),
                                         end_date=None,
                                         version=Version.LOTV)
        self.s17 = self.db.create_season(id=17,
                                         start_date=None,
                                         end_date=None,
                                         version=Version.LOTV)

        # Create a present ladder.

        self.l99 = self.db.create_ladder(bid=99, season=self.s16)

    def fetch_new(self, **kwargs):
        fetch_new(region=Region.EU, bnet_client=self.bnet, **kwargs)

    def fetch_new_in_league(self, region=Region.EU, season=None, version=Version.HOTS, mode=Mode.TEAM_1V1,
                            league=League.GOLD):
        fetch_new_in_league(lambda: None, self.bnet, region, season or self.db.season, version, mode, league)

    def test_normal_fetch_creates_a_new_ladder_in_season(self):
        self.mock_fetch_league(t0_bids=[99, 100], season_id=self.s16.id)
        self.mock_fetch_ladder()

        self.fetch_new_in_league(season=self.s16)

        self.bnet.fetch_ladder.assert_called_once_with(self.s16.id, Region.EU, 100)

        ladder = self.db.get(Ladder, bid=100, region=Region.EU)

        self.assertEqual(Version.HOTS, ladder.version)
        self.assertEqual(Mode.TEAM_1V1, ladder.mode)
        self.assertEqual(League.GOLD, ladder.league)
        self.assertEqual(Ladder.GOOD, ladder.strangeness)
        self.assertEqual(self.s16.id, ladder.season_id)
        self.assertEqual([100], [c.bid for c in ladder.sources.all()])

        self.assertEqual({99, 100}, {l.bid for l in self.db.all(Ladder)})

    def test_new_season_detection_creates_a_new_season(self):
        self.mock_current_season(season_id=17, start_time=self.datetime(days=0))

        self.fetch_new()

        self.bnet.fetch_current_season.assert_called_once_with(Region.EU)

        self.assertEqual(0, self.db.count(Ladder, bid=100, region=Region.EU))

        s16 = self.db.get(Season, pk=16)
        s17 = self.db.get(Season, pk=17)
        s18 = self.db.get(Season, pk=18)

        self.assertEqual(self.date(), s16.end_date)
        self.assertEqual(self.date(days=1), s17.start_date)
        self.assertEqual(None, s17.end_date)
        self.assertEqual(None, s18.start_date)
        self.assertEqual(None, s18.end_date)

    def test_fetching_stops_on_503_ladder_fetch(self):
        self.mock_current_season(status=503)
        self.fetch_new()
        self.assertEqual(5, self.bnet.fetch_current_season.call_count)

