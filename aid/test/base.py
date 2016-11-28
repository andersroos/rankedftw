import inspect
import os
import sys
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock
from urllib.error import HTTPError

import django
import django.db
import django.test.runner
import django.test.testcases
import django.test.utils
from django.test import TestCase

from aid.test.data import gen_member, gen_api_ladder
from aid.test.db import Db
from common.utils import to_unix, utcnow, classinstancemethod
from lib import sc2
from main.battle_net import LeagueResponse, ApiLeague, SeasonResponse, ApiSeason, LadderResponse, BnetClient
from main.models import Region, Enums, Mode, Version, League


# warnings.filterwarnings('ignore')


class DjangoTestCase(TestCase):
    # This is really ugly hack of django test framework. This was made a long time ago maybe possible to make it
    # better now, since djanog test framwork have been changed a lot. The c++ code needs to access the database so
    # the django postgresql test rollback scheme does not really work. Since using postgresql like this makes the
    # tests so slow sqlite is used for tests that doew not require postgresql. This makes it impossible to run
    # them in the same process.
    #
    # Sometimes it is useful to debug the db. Set the KEEP_DATA environment variable to prevent deletion of the
    # database.

    maxDiff = 1e4

    def __str__(self):
        """ Return a string that can be used as a command line argument to nose. """
        return "%s:%s.%s" % (inspect.getfile(self.__class__), self.__class__.__name__, self._testMethodName)

    @classmethod
    def _enter_atomics(cls):
        # Prevent rollbacks.
        pass

    @classmethod
    def _rollback_atomics(cls, atomics):
        # Prevent rollbacks.
        pass

    def _fixture_teardown(self):
        # Prevent clearing of test data.
        pass

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.runner = django.test.runner.DiscoverRunner(interactive=False)
        django.test.utils.setup_test_environment()
        self.old_config = self.runner.setup_databases()
        self.db = Db()

    @classmethod
    def tearDownClass(self):
        if 'KEEP_DATA' in os.environ:
            print("\nkeeping test database: %r." % self.db.db_name, file=sys.stderr)
        else:
            self.db.delete_all()
            self.runner.teardown_databases(self.old_config)
            django.test.utils.teardown_test_environment()
        super().tearDownClass()

    def tearDown(self):
        if hasattr(self, 'cpp') and self.cpp is not None:
            self.cpp.release()
            self.cpp = None
        super().tearDown()

    def load(self):
        self.cpp = sc2.RankingData(self.db.db_name, Enums.INFO)
        self.cpp.load(self.db.ranking.id)

    def process_ladder(self, load=False, save=False, region=Region.EU, fetch_time=None,
                       mode=Mode.TEAM_1V1, version=Version.HOTS, league=League.GOLD, season=None, tier=0,
                       members=None, **kwargs):
        """ Update a ranking building single member with kwargs or use members if set. """

        season = season or self.db.season
        fetch_time = fetch_time or utcnow()
        members = members or [gen_member(**kwargs)]

        if not getattr(self, 'cpp', None):
            self.cpp = sc2.RankingData(self.db.db_name, Enums.INFO)

        if load:
            self.load()

        self.cpp.update_with_ladder(0,  # bid
                                    0,  # source_id
                                    region,
                                    mode,
                                    league,
                                    tier,
                                    version,
                                    season.id,
                                    to_unix(fetch_time),
                                    Mode.team_size(mode),
                                    members)
        if save:
            self.save_to_ranking()

    def save_to_ranking(self):
        self.cpp.save_data(self.db.ranking.id, self.db.ranking.season_id, to_unix(utcnow()))

    @classinstancemethod
    def date(self, **kwargs):
        return self.today + timedelta(**kwargs)

    @classinstancemethod
    def datetime(self, **kwargs):
        return self.now + timedelta(**kwargs)

    @classinstancemethod
    def unix_time(self, **kwargs):
        return to_unix(self.now + timedelta(**kwargs))

    def assert_team_ranks(self, ranking_id, *ranks, skip_len=False, sort=True):
        """ Get all team ranks using the current ranking id and assert that all ranks corresponds to team ranks in
        db. All keys in ranks will be verified against team ranks values. """

        team_ranks = sc2.get_team_ranks(self.db.db_name, ranking_id, sort)

        try:
            if not skip_len:
                self.assertEqual(len(team_ranks), len(ranks))
            for i, (team_rank, r) in enumerate(zip(team_ranks, ranks), start=1):
                for key, value in r.items():
                    self.assertEqual(value, team_rank[key], msg="%s wrong @ rank %d, expected %r, was %r" %
                                     (key, i, r, {key: team_rank.get(key, None) for key in r.keys()}))
        except AssertionError:
            print("Expected:\n%s" % "\n".join([repr(tr) for tr in ranks]))
            print("Actual:\n%s" % "\n".join([repr(tr) for tr in team_ranks]))
            raise


class MockBnetTestMixin(object):
    """ Class to help with common mockings. """

    def setUp(self):
        super().setUp()
        self.bnet = BnetClient()

    def mock_raw_get(self, status=200, content=""):
        self.bnet.raw_get = Mock(side_effect=HTTPError('', status, '', '', StringIO(content)))
        
    def mock_current_season(self, status=200, season_id=None, start_time=None, fetch_time=None):
        self.bnet.fetch_current_season = \
            Mock(return_value=SeasonResponse(status,
                                             ApiSeason({'id': season_id or self.db.season.id,
                                                        'start_timestamp': to_unix(start_time or utcnow())},
                                                       'http://fake-url'),
                                             fetch_time or utcnow(), 0))
        
    def mock_fetch_ladder(self, status=200, fetch_time=None, members=None, **kwargs):
        self.bnet.fetch_ladder = \
            Mock(return_value=LadderResponse(status, gen_api_ladder(members, **kwargs), fetch_time or utcnow(), 0))

    def mock_fetch_league(self, status=200, fetch_time=None, season_id=None, t0_bids=None, t1_bids=None, t2_bids=None):
        season_id = season_id or self.db.season.id
        self.bnet.fetch_league = \
            Mock(return_value=LeagueResponse(status,
                                             ApiLeague({'tier': [
                                                 {'id': 0, 'division': [{'ladder_id': lid} for lid in t0_bids or []]},
                                                 {'id': 1, 'division': [{'ladder_id': lid} for lid in t1_bids or []]},
                                                 {'id': 2, 'division': [{'ladder_id': lid} for lid in t2_bids or []]},
                                             ]}, url="http://fake-url", bid=season_id * 100000),
                                             fetch_time or utcnow(), 0))
        
