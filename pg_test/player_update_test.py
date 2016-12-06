import aid.test.init_django_postgresql

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from common.utils import utcnow
from main.models import Season, Race, Mode, League, Player


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.s1 = self.db.create_season(id=1)
        self.s2 = self.db.create_season(id=2)

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.db.delete_all(keep=[Season])
        self.db.create_ranking()

    def test_player_season_is_updated_if_greater_than_current(self):
        self.db.create_player(bid=301,
                              name='arne0',
                              clan='arne0',
                              tag='arne0',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.TEAM_1V1)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.GOLD,
                            season=self.s2,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.TEAM_1V1, p.mode)
        self.assertEqual(self.s2.id, p.season_id)

    def test_player_name_is_not_updated_but_other_info_is_if_new_name_is_empty__this_handles_bug_in_blizzard_api(self):
        self.db.create_player(bid=301,
                              name='arne0',
                              clan='arne0',
                              tag='arne0',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.TEAM_1V1)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.GRANDMASTER,
                            season=self.s2,
                            bid=301,
                            name="",
                            tag="",
                            clan="",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne0", p.name)
        self.assertEqual("arne0", p.clan)
        self.assertEqual("arne0", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GRANDMASTER, p.league)
        self.assertEqual(Mode.TEAM_1V1, p.mode)
        self.assertEqual(self.s2.id, p.season_id)

    def test_race_mode_and_league_within_season_is_not_updated_if_mode_11_is_already_set(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.TEAM_1V1)

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            league=League.PLATINUM,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.ZERG)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.TEAM_1V1, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_race_is_updated_if_everything_else_is_the_same(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.RANDOM_2V2)

        self.process_ladder(mode=Mode.RANDOM_2V2,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.ZERG)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.ZERG, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.RANDOM_2V2, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_race_is_updated_if_everything_else_is_the_same__but_not_if_1v1(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.TEAM_1V1)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.ZERG)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.TEAM_1V1, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_three_ladders_to_see_that_correct_player_version_sticks_in_cache(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.RANDOM_3V3)

        # Loaded to cache, not updated.
        self.process_ladder(mode=Mode.RANDOM_3V3,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        p = self.db.get(Player, bid=301)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.RANDOM_3V3, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

        # Updated in db (and hopefully in cache).
        self.process_ladder(mode=Mode.RANDOM_2V2,
                            league=League.DIAMOND,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.ZERG)

        p = self.db.get(Player, bid=301)
        self.assertEqual(Race.ZERG, p.race)
        self.assertEqual(League.DIAMOND, p.league)
        self.assertEqual(Mode.RANDOM_2V2, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

        # Not updated if compared to cached version as it should.
        self.process_ladder(mode=Mode.RANDOM_4V4,
                            league=League.PLATINUM,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.PROTOSS)

        p = self.db.get(Player, bid=301)
        self.assertEqual(Race.ZERG, p.race)
        self.assertEqual(League.DIAMOND, p.league)
        self.assertEqual(Mode.RANDOM_2V2, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_race_is_updated_if_everything_else_is_the_same_even_if_mode_is_not_1v1(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.RANDOM_3V3)

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.ZERG)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.ZERG, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.RANDOM_3V3, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_league_is_updated_if_better_league_and_another_mode_but_not_11_and_same_season(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.RANDOM_3V3)

        self.process_ladder(mode=Mode.RANDOM_4V4,
                            league=League.PLATINUM,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.PLATINUM, p.league)
        self.assertEqual(Mode.RANDOM_4V4, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_league_is_not_updated_if_worse_league_and_another_mode_but_not_11_and_same_season(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.PLATINUM,
                              mode=Mode.RANDOM_3V3)

        self.process_ladder(mode=Mode.RANDOM_4V4,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.PLATINUM, p.league)
        self.assertEqual(Mode.RANDOM_3V3, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_league_is_updated_to_lower_within_mode_if_nothing_else_changes(self):
        self.db.create_player(bid=301,
                              name='arne1',
                              clan='arne1',
                              tag='arne1',
                              season=self.s1,
                              race=Race.TERRAN,
                              league=League.PLATINUM,
                              mode=Mode.RANDOM_3V3)

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.RANDOM_3V3, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_update_from_null_works(self):
        self.db.create_player(bid=301,
                              name="arne1",
                              tag="",
                              clan="",
                              mode=None,
                              league=None,
                              race=None,
                              season=None)

        self.process_ladder(mode=Mode.RANDOM_3V3,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne1", p.name)
        self.assertEqual("arne1", p.clan)
        self.assertEqual("arne1", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.RANDOM_3V3, p.mode)
        self.assertEqual(self.s1.id, p.season_id)

    def test_season_is_not_updated_if_season_if_after_player_season(self):

        self.db.create_player(bid=301,
                              name='arne0',
                              clan='arne0',
                              tag='arne0',
                              season=self.s2,
                              race=Race.TERRAN,
                              league=League.GOLD,
                              mode=Mode.TEAM_1V1)

        self.process_ladder(mode=Mode.TEAM_1V1,
                            league=League.GOLD,
                            season=self.s1,
                            bid=301,
                            name="arne1",
                            tag="arne1",
                            clan="arne1",
                            race=Race.TERRAN)

        self.assertEqual(1, len(Player.objects.all()))

        p = self.db.get(Player, bid=301)
        self.assertEqual("arne0", p.name)
        self.assertEqual("arne0", p.clan)
        self.assertEqual("arne0", p.tag)
        self.assertEqual(Race.TERRAN, p.race)
        self.assertEqual(League.GOLD, p.league)
        self.assertEqual(Mode.TEAM_1V1, p.mode)
        self.assertEqual(self.s2.id, p.season_id)
