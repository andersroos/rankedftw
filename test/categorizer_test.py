import itertools

import aid.test.init_django_sqlite

from aid.test.base import DjangoTestCase
from datetime import datetime

from aid.test.data import gen_api_ladder, gen_member
from main.battle_net import ApiLadder
from main.battle_net import ApiPlayerLadders
from main.categorizer import get_season_based_on_join_times, determine_season, get_strangeness, get_version_mode_league
from common.utils import utcnow, uniqueid
from django.utils import timezone
from main.models import Version, Mode, League, Season
from main.models import Ladder


def gen_api_data(l_bid, *p_bids, mmq="HOTS_SOLO", league="SILVER", race="ZERG",
                 join_time=None, join_times=None, season="currentSeason", team_size=None):
    """ Generate api data from blizzard. Returns <ladder_data,
    player_ladder_data>. Player ladder data will contain one team. """

    join_time = join_time or utcnow()
    join_times = join_times or [join_time]

    team_size = team_size or len(p_bids)

    names = [uniqueid(10) for _ in p_bids]

    pld = {"ladderId": l_bid,
           "league": league,
           "matchMakingQueue": mmq,
           "wins": 20,
           "losses": 22}

    ppds = [{"id": p_bid, "realm": 1, "displayName": name, "profilePath": "/profile/%d/1/%s/" % (p_bid, name)}
            for p_bid, name in zip(p_bids, names)]

    members = [{"character": {"id": p_bid, "realm": 1, "profilePath": "/profile/%d/1/%s/" % (p_bid, name)},
                "joinTimestamp": int(jt.strftime("%s")),
                "points": 102.2,
                "wins": 20,
                "losses": 22,
                "favoriteRaceP1": race}
               for p_bid, jt, name in zip(p_bids, itertools.cycle(join_times), names)]

    for member in members:
        if team_size > 1: member['favoriteRaceP2'] = race
        if team_size > 2: member['favoriteRaceP3'] = race
        if team_size > 3: member['favoriteRaceP4'] = race

    l = {"ladderMembers": members}
    p = {season: [{"ladder": [pld], "characters": ppds}]}

    # To simplify l_bid = p_bid.
    return ApiLadder(l, '/ladder/%d/' % l_bid), ApiPlayerLadders(p, '/profile/%d/' % l_bid)


class DetermineSeasonTest(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.now = utcnow()
        self.today = self.now.date()

        self.s10 = self.db.create_season(id=10,
                                         start_date=self.date(days=1000),
                                         end_date=self.date(days=1099))
        self.s11 = self.db.create_season(id=11,
                                         start_date=self.date(days=1100),
                                         end_date=self.date(days=1199))
        self.s12 = self.db.create_season(id=12,
                                         start_date=self.date(days=1200),
                                         end_date=self.date(days=1299))
        self.s13 = self.db.create_season(id=13,
                                         start_date=self.date(days=1300),
                                         end_date=None)
        self.s14 = self.db.create_season(id=14,
                                         start_date=None,
                                         end_date=None)

    def prep(self, player=False, season='no_season', fetch_time=0, join_time=0, first_join=0, last_join=0):
        fetch_time = self.datetime(days=fetch_time)

        if join_time:
            al, ap = gen_api_data(1, 301, join_time=self.datetime(days=join_time), season=season)
            join_season, join_valid = get_season_based_on_join_times(al.first_join(), al.last_join())

        else:
            al, ap = gen_api_data(1, 301, 302, 302,
                                  join_times=[self.datetime(days=first_join), self.datetime(days=last_join)],
                                  season=season, team_size=1)
            join_season, join_valid = get_season_based_on_join_times(al.first_join(), al.last_join())

        if player:
            return determine_season(fetch_time=fetch_time, match=ap.refers(1),
                                    join_season=join_season, join_valid=join_valid)

        else:
            return join_season, join_valid

    def setUp(self):
        super().setUp()
        self.db.all(Ladder).delete()

    # Open season tests.

    def test__prev__fetch_mid_13__first_join_end_12__last_join_sta_13__is_12_can_be_13(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1350, first_join=1299, last_join=1300)
        self.assertEqual(self.s12.id, season.id)
        self.assertEqual(1, valid)

    def test__prev__fetch_mid_13__first_join_mid_13__last_join_mid_13__is_13(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1350, first_join=1350, last_join=1350)
        self.assertEqual(self.s13.id, season.id)
        self.assertEqual(0, valid)

    def test__prev__fetch_mid_13__first_join_sta_13__last_join_mid_13__is_13(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1350, first_join=1300, last_join=1350)
        self.assertEqual(self.s13.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_mid_13__first_join_sta_13__last_join_mid_13__is_13(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1350, first_join=1300, last_join=1350)
        self.assertEqual(self.s13.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_mid_13__first_join_mid_13__last_join_mid_13__is_13_can_be_14(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1350, first_join=1350, last_join=1350)
        self.assertEqual(self.s13.id, season.id)
        self.assertEqual(1, valid)

    # Non open season tests.

    def test__curr__fetch_mid_12__first_join_mid_12__last_join_mid_12__is_12(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1250, first_join=1250, last_join=1250)
        self.assertEqual(self.s12.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_sta_12__join_end_10__is_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1200, join_time=1099)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_end_11__join_end_12__is_12(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1199, join_time=1299)
        self.assertEqual(self.s12.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_mid_11__join_mid_11__is_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1150, join_time=1150)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_end_11__join_end_11__is_11_can_be_12(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1199, join_time=1199)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(1, valid)

    def test__prev__fetch_sta_12__join_end_11__is_11(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1200, join_time=1199)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__prev__fetch_sta_12__join_sta_12__is_11(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1200, join_time=1200)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__prev__fetch_sta_12__join_sta_11__is_11_can_be_10(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1200, join_time=1100)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(-1, valid)

    def test__curr__fetch_sta_11__join_sta_11__is_11_can_be_10(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1100, join_time=1100)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(-1, valid)

    def test__prev__fetch_sta_11__join_end_10__is_10(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1100, join_time=1099)
        self.assertEqual(self.s10.id, season.id)
        self.assertEqual(0, valid)

    def test__prev__fetch_mid_11__join_end_10__is_10(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1150, join_time=1099)
        self.assertEqual(self.s10.id, season.id)
        self.assertEqual(0, valid)

    def test__prev__fetch_sta_12__join_end_10__is_11_can_be_10(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1200, join_time=1099)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(-1, valid)

    def test__curr__fetch_end_11__first_join_end_10__last_join_mid_11__is_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1199, first_join=1099, last_join=1150)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_sta_12__first_join_end_10__last_join_end_11__is_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1200, first_join=1099, last_join=1199)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_sta_12__first_join_mid_11__last_join_sta_12__is_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1200, first_join=1150, last_join=1200)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_sta_12__first_join_end_11__last_join_sta_12__is_12_can_be_11(self):
        season, valid = self.prep(player=True, season="currentSeason",
                                  fetch_time=1200, first_join=1199, last_join=1200)
        self.assertEqual(self.s12.id, season.id)
        self.assertEqual(-1, valid)

    def test__prev__fetch_sta_12__first_join_end_11__last_join_sta_12__is_11(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1200, first_join=1199, last_join=1200)
        self.assertEqual(self.s11.id, season.id)
        self.assertEqual(0, valid)

    def test__curr__fetch_sta_13__first_join_end_11__last_join_sta_13__is_12(self):
        season, valid = self.prep(player=True, season="previousSeason",
                                  fetch_time=1300, first_join=1199, last_join=1300)
        self.assertEqual(self.s12.id, season.id)
        self.assertEqual(0, valid)

    def test__no_player__fetch_mid_12__join_mid_10__is_10(self):
        season, valid = self.prep(player=False, fetch_time=1250, join_time=1050)
        self.assertEqual(self.s10.id, season.id)
        self.assertEqual(0, valid)

    def test__no_player__fetch_end_12__join_end_10__is_10_can_be_10(self):
        season, valid = self.prep(player=False, fetch_time=1299, join_time=1099)
        self.assertEqual(self.s10.id, season.id)
        self.assertEqual(1, valid)

    def test__no_player__fetch_beg_12__join_sta_10__is_10_can_be_9(self):
        season, valid = self.prep(player=False, fetch_time=1200, join_time=1000)
        self.assertEqual(self.s10.id, season.id)
        self.assertEqual(-1, valid)

    def test__no_player__fetch_mid_13__first_join_mid_10__last_join_sta_13__is_exception(self):
        with self.assertRaises(Exception) as e:
            self.prep(player=False,
                      fetch_time=1399, first_join=1050, last_join=1300)
            self.assertIn("too far apart", str(e.exception))


class VersionModeLeaueTest(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.s10 = self.db.create_season(id=10,
                                         version=Version.WOL,
                                         start_date='2011-01-11',
                                         end_date='2011-11-03')
        self.s16 = self.db.create_season(id=16,
                                         start_date='2013-11-11',
                                         end_date='2014-01-03')
        self.time = datetime(2013, 12, 20, 12, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Season])

    def test_mmq_version_and_league_from_player_info(self):
        al, ap = gen_api_data(1, 301, mmq="SOLO", league="BRONZE", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_1V1, mode)
        self.assertEqual(League.BRONZE, league)
        self.assertEqual(Version.WOL, version)

        al, ap = gen_api_data(2, 302, mmq="HOTS_TWOS", league="GOLD", join_time=self.time)
        version, mode, league = get_version_mode_league(2, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_2V2, mode)
        self.assertEqual(League.GOLD, league)
        self.assertEqual(Version.HOTS, version)

        al, ap = gen_api_data(3, 303, mmq="THREES", league="PLATINUM", join_time=self.time)
        version, mode, league = get_version_mode_league(3, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_3V3, mode)
        self.assertEqual(League.PLATINUM, league)
        self.assertEqual(Version.WOL, version)

        al, ap = gen_api_data(4, 304, 314, 324, mmq="HOTS_THREES", league="DIAMOND", join_time=self.time)
        version, mode, league = get_version_mode_league(4, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_3V3, mode)
        self.assertEqual(League.DIAMOND, league)
        self.assertEqual(Version.HOTS, version)

        al, ap = gen_api_data(5, 305, mmq="THREES", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(5, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_3V3, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.WOL, version)

        al, ap = gen_api_data(6, 306, mmq="FOURS", league="GRANDMASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(6, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_4V4, mode)
        self.assertEqual(League.GRANDMASTER, league)
        self.assertEqual(Version.WOL, version)

        al, ap = gen_api_data(7, 307, 317, 327, 337, mmq="HOTS_FOURS", league="GRANDMASTER", race=337,
                              join_time=self.time)
        version, mode, league = get_version_mode_league(7, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_4V4, mode)
        self.assertEqual(League.GRANDMASTER, league)
        self.assertEqual(Version.HOTS, version)

    def test_categorize_without_ap_season_10_to_wol(self):
        al, ap = gen_api_data(1, 301, mmq="WOL_SOLO", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s10, al, None)
        self.assertEqual(Mode.UNKNOWN, mode)
        self.assertEqual(League.UNKNOWN, league)
        self.assertEqual(Version.WOL, version)

    def test_categorize_without_ap_team_2v2(self):
        al, ap = gen_api_data(1, 301, 302, mmq="LOTV_TWOS", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, None)
        self.assertEqual(Mode.TEAM_2V2, mode)
        self.assertEqual(League.UNKNOWN, league)
        self.assertEqual(Version.UNKNOWN, version)

    def test_categorize_without_ap_team_3v3(self):
        al, ap = gen_api_data(1, 301, 302, 303, mmq="LOTV_THREES", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, None)
        self.assertEqual(Mode.TEAM_3V3, mode)
        self.assertEqual(League.UNKNOWN, league)
        self.assertEqual(Version.UNKNOWN, version)

    def test_categorize_without_ap_team_4v4(self):
        al, ap = gen_api_data(1, 301, 302, 303, 304, mmq="LOTV_FOURS", league="MASTER", race=304, join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, None)
        self.assertEqual(Mode.TEAM_4V4, mode)
        self.assertEqual(League.UNKNOWN, league)
        self.assertEqual(Version.UNKNOWN, version)

    def test_lotv_categorizing_team_4v4(self):
        al, ap = gen_api_data(1, 301, 302, 303, 304, mmq="LOTV_FOURS", league="MASTER", race=304, join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_4V4, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_random_4v4(self):
        al, ap = gen_api_data(1, 301, mmq="LOTV_FOURS", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_4V4, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_team_3v3(self):
        al, ap = gen_api_data(1, 301, 302, 303, mmq="LOTV_THREES", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_3V3, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_random_3v3(self):
        al, ap = gen_api_data(1, 301, mmq="LOTV_THREES", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_3V3, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_team_2v2(self):
        al, ap = gen_api_data(1, 301, 302, mmq="LOTV_TWOS", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_2V2, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_random_2v2(self):
        al, ap = gen_api_data(1, 301, mmq="LOTV_TWOS", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.RANDOM_2V2, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_archon(self):
        al, ap = gen_api_data(1, 301, 302, mmq="LOTV_TWOS_COMP", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.ARCHON, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)

    def test_lotv_categorizing_1v1(self):
        al, ap = gen_api_data(1, 301, mmq="LOTV_SOLO", league="MASTER", join_time=self.time)
        version, mode, league = get_version_mode_league(1, self.s16, al, ap)
        self.assertEqual(Mode.TEAM_1V1, mode)
        self.assertEqual(League.MASTER, league)
        self.assertEqual(Version.LOTV, version)


class DetermineStrangenessTest(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.now = utcnow()
        self.today = self.now.date()
        self.s14 = self.db.create_season(id=14,
                                         start_date=self.date(days=-299),
                                         end_date=self.date(days=-200))
        self.s15 = self.db.create_season(id=15,
                                         start_date=self.date(days=-199),
                                         end_date=self.date(days=-100))
        self.s16 = self.db.create_season(id=16,
                                         start_date=self.date(days=-99),
                                         end_date=None)
        self.s14_time = self.datetime(days=-250)
        self.s15_time = self.datetime(days=-150)
        self.s16_time = self.datetime(days=-50)

        self.db.create_cache()
        self.db.create_ladder()
        self.db.create_ranking()
        self.db.create_player()
        self.db.create_team()

    def test_categorize_as_genuine_strange_imediatly(self):
        al = gen_api_ladder(members=[
            gen_member(points=1.2, join_time=self.s16_time),
        ], gd=False)
        self.assertEqual(Ladder.STRANGE, get_strangeness(self.datetime(), al, ap=None))

    def test_categorize_as_nyd_if_unceritain_time_low_points_and_no_ap(self):
        al = gen_api_ladder(members=[
            gen_member(points=1, join_time=self.datetime(days=-7)),
        ], gd=False)
        self.assertEqual(Ladder.NYD, get_strangeness(self.datetime(), al, ap=None))

    def test_categorize_as_nop_if_ceritain_time_good_points_and_no_ap(self):
        al = gen_api_ladder(members=[
            gen_member(points=1, join_time=self.datetime(days=-20)),
        ], gd=False)
        self.assertEqual(Ladder.NOP, get_strangeness(self.datetime(), al, ap=None))

    def test_categorize_as_good_if_ap(self):
        al = gen_api_ladder(members=[
            gen_member(points=1, join_time=self.datetime(days=-7)),
        ], gd=False)
        self.assertEqual(Ladder.GOOD, get_strangeness(self.datetime(), al, ap=1))

    def test_exception_if_ap_and_strange_points(self):
        al = gen_api_ladder(members=[
            gen_member(points=1.1, join_time=self.datetime(days=-7)),
        ], gd=False)
        with self.assertRaises(Exception):
            get_strangeness(self.datetime(), al, ap=1)

    def test_what_happens_if_low_member_count_and_random_strange_but_even_(self):
        al = gen_api_ladder(members=[
            gen_member(points=1, join_time=self.datetime(days=-20)),
        ], gd=False)
        self.assertEqual(Ladder.NOP, get_strangeness(self.datetime(), al, ap=None))
