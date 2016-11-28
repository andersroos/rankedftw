import aid.test.init_django_postgresql
from aid.test.data import gen_member

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from main.models import Season, Version, Team, Player, Mode, Race
from main.models import League
from common.utils import utcnow


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.s1 = self.db.create_season(id=1)
        self.s2 = self.db.create_season(id=2)
        self.s3 = self.db.create_season(id=3)

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.db.delete_all(keep=[Season])
        self.ladder = self.db.create_ladder(bid=1, created=self.datetime(seconds=1))  # Always using same ladder.

    def test_team_is_updated_with_both_version_and_league_with_new_season(self):
        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.HOTS,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.db.create_ranking(season=self.s2)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s2,
                            version=Version.WOL,
                            league=League.GOLD,
                            members=[gen_member(bid=301, race=Race.ZERG)])

        self.assertEqual(1, len(Team.objects.all()))

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s2, t1.season)
        self.assertEqual(Version.WOL, t1.version)
        self.assertEqual(League.GOLD, t1.league)

    def test_team_is_updated_with_both_version_and_league_with_new_season_test_2(self):
        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.WOL,
                                 league=League.GOLD,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.db.create_ranking(season=self.s2)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s2,
                            version=Version.HOTS,
                            league=League.PLATINUM,
                            members=[gen_member(bid=301, race=Race.ZERG)])

        self.assertEqual(1, len(Team.objects.all()))

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s2, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.PLATINUM, t1.league)

    def test_update_of_version_to_later_version_is_updated_within_same_season(self):
        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.WOL,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s1,
                            version=Version.HOTS,
                            league=League.GOLD,
                            members=[gen_member(bid=301, race=Race.ZERG)])

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s1, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.GOLD, t1.league)

    def test_update_of_version_to_earlier_version_is_not_updated_when_in_same_season(self):
        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.HOTS,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s1,
                            version=Version.WOL,
                            league=League.GRANDMASTER,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s1, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.PLATINUM, t1.league)

    def test_update_of_league_is_updated_when_version_and_season_is_then_same_1(self):
        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.HOTS,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s1,
                            version=Version.HOTS,
                            league=League.GRANDMASTER,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s1, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.GRANDMASTER, t1.league)

    def test_update_of_league_is_updated_when_version_and_season_is_then_same_2(self):

        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.HOTS,
                                 league=League.GRANDMASTER,
                                 member0=p1,
                                 race0=Race.ZERG)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s1,
                            version=Version.HOTS,
                            league=League.PLATINUM,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s1, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.PLATINUM, t1.league)

    def test_three_ladders_to_see_that_correct_team_version_sticks_in_cache(self):

        p1 = self.db.create_player(bid=301,
                                   race=Race.ZERG)

        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.s1,
                                 version=Version.HOTS,
                                 league=League.PLATINUM,
                                 member0=p1,
                                 race0=Race.ZERG)

        # Loaded to cache, not updated.

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s1,
                            version=Version.HOTS,
                            league=League.PLATINUM,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s1, t1.season)
        self.assertEqual(Version.HOTS, t1.version)
        self.assertEqual(League.PLATINUM, t1.league)

        # Updated in db (and hopefully in cache).

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s3,
                            version=Version.WOL,
                            league=League.GOLD,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s3, t1.season)
        self.assertEqual(Version.WOL, t1.version)
        self.assertEqual(League.GOLD, t1.league)

        # Not updated if compared to cached version as it should.

        self.process_ladder(mode=Mode.TEAM_1V1,
                            season=self.s2,
                            version=Version.LOTV,
                            league=League.GRANDMASTER,
                            bid=301,
                            race=Race.ZERG)

        t1 = self.db.get(Team, member0=self.db.get(Player, bid=301))

        self.assertEqual(self.s3, t1.season)
        self.assertEqual(Version.WOL, t1.version)
        self.assertEqual(League.GOLD, t1.league)
