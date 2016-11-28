import aid.test.init_django_postgresql
from aid.test.data import gen_member

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from common.utils import utcnow
from main.models import Season, League, Mode, Player, Team, Race


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()
        self.db.create_season(id=1)

    def setUp(self):
        super().setUp()
        self.now = utcnow()
        self.db.delete_all(keep=[Season])
        self.ladder = self.db.create_ladder(bid=1, created=self.datetime(seconds=1))  # Always using same ladder.

    def test_non_existent_4v4_team_is_created(self):
        self.process_ladder(mode=Mode.TEAM_4V4,
                            members=[gen_member(bid=301, race=Race.ZERG),
                                     gen_member(bid=302, race=Race.PROTOSS),
                                     gen_member(bid=303, race=Race.TERRAN),
                                     gen_member(bid=304, race=Race.TERRAN)])
        
        p1 = self.db.get(Player, bid=301)
        p2 = self.db.get(Player, bid=302)
        p3 = self.db.get(Player, bid=303)
        p4 = self.db.get(Player, bid=304)
        t1 = self.db.all(Team)[0]
        self.assertEqual(1, len(self.db.all(Team)))
        self.assertEqual(Mode.TEAM_4V4, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(p2.id, t1.member1_id)
        self.assertEqual(p3.id, t1.member2_id)
        self.assertEqual(p4.id, t1.member3_id)
        self.assertEqual(Race.ZERG,    t1.race0)
        self.assertEqual(Race.PROTOSS, t1.race1)
        self.assertEqual(Race.TERRAN,  t1.race2)
        self.assertEqual(Race.TERRAN,  t1.race3)

    def test_process_two_4v4_ladders_with_the_same_team_but_different_order_just_creates_one_team(self):
        self.process_ladder(mode=Mode.TEAM_4V4,
                            members=[gen_member(bid=301, race=Race.ZERG),
                                     gen_member(bid=302, race=Race.PROTOSS),
                                     gen_member(bid=303, race=Race.TERRAN),
                                     gen_member(bid=304, race=Race.RANDOM)])

        self.process_ladder(mode=Mode.TEAM_4V4,
                            members=[gen_member(bid=304, race=Race.RANDOM),
                                     gen_member(bid=303, race=Race.TERRAN),
                                     gen_member(bid=302, race=Race.PROTOSS),
                                     gen_member(bid=301, race=Race.ZERG)])

        self.assertEqual(1, len(self.db.all(Team)))

        p1 = self.db.get(Player, bid=301)
        p2 = self.db.get(Player, bid=302)
        p3 = self.db.get(Player, bid=303)
        p4 = self.db.get(Player, bid=304)
        t1 = self.db.all(Team)[0]

        self.assertEqual(1, len(self.db.all(Team)))
        self.assertEqual(Mode.TEAM_4V4, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(p2.id, t1.member1_id)
        self.assertEqual(p3.id, t1.member2_id)
        self.assertEqual(p4.id, t1.member3_id)
        self.assertEqual(Race.ZERG,    t1.race0)
        self.assertEqual(Race.PROTOSS, t1.race1)
        self.assertEqual(Race.TERRAN,  t1.race2)
        self.assertEqual(Race.RANDOM,  t1.race3)

    def test_process_two_3v3_ladders_with_the_same_team_but_different_order_just_creates_one_team(self):
        self.process_ladder(mode=Mode.TEAM_3V3,
                            members=[gen_member(bid=301, race=Race.ZERG),
                                     gen_member(bid=302, race=Race.PROTOSS),
                                     gen_member(bid=303, race=Race.TERRAN)])

        self.process_ladder(mode=Mode.TEAM_3V3,
                            members=[gen_member(bid=303, race=Race.TERRAN),
                                     gen_member(bid=302, race=Race.PROTOSS),
                                     gen_member(bid=301, race=Race.ZERG)])

        self.assertEqual(1, len(self.db.all(Team)))

        p1 = self.db.get(Player, bid=301)
        p2 = self.db.get(Player, bid=302)
        p3 = self.db.get(Player, bid=303)
        t1 = self.db.all(Team)[0]

        self.assertEqual(Mode.TEAM_3V3, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(p2.id, t1.member1_id)
        self.assertEqual(p3.id, t1.member2_id)
        self.assertEqual(None,  t1.member3_id)
        self.assertEqual(Race.ZERG,     t1.race0)
        self.assertEqual(Race.PROTOSS,  t1.race1)
        self.assertEqual(Race.TERRAN,   t1.race2)
        self.assertEqual(Race.UNKNOWN,  t1.race3)

    def test_process_two_2v2_ladders_with_the_same_team_but_different_order_just_creates_one_team(self):
        self.process_ladder(mode=Mode.TEAM_2V2, members=[gen_member(bid=301, race=Race.ZERG),
                                                         gen_member(bid=302, race=Race.PROTOSS)])

        self.assertEqual(1, len(self.db.all(Team)))

        p1 = self.db.get(Player, bid=301)
        p2 = self.db.get(Player, bid=302)
        t1 = self.db.all(Team)[0]

        self.assertEqual(Mode.TEAM_2V2, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(p2.id, t1.member1_id)
        self.assertEqual(None,  t1.member2_id)
        self.assertEqual(None,  t1.member3_id)
        self.assertEqual(Race.ZERG,     t1.race0)
        self.assertEqual(Race.PROTOSS,  t1.race1)
        self.assertEqual(Race.UNKNOWN,  t1.race2)
        self.assertEqual(Race.UNKNOWN,  t1.race3)

    def test_existent_random_4v4_is_updated_with_changed_race(self):
        p1 = self.db.create_player(bid=301)
        t1 = self.db.create_team(mode=Mode.RANDOM_4V4,
                                 member0=p1,
                                 season=self.db.season,
                                 race0=Race.TERRAN)

        self.process_ladder(mode=Mode.RANDOM_4V4, bid=301, race=Race.ZERG)

        self.assertEqual(1, len(self.db.all(Team)))

        p1 = self.db.get(Player, bid=301)
        t1 = self.db.get(Team, id=t1.pk)
        self.assertEqual(1, len(Team.objects.all()))
        self.assertEqual(Mode.RANDOM_4V4, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(None,  t1.member1_id)
        self.assertEqual(None,  t1.member2_id)
        self.assertEqual(None,  t1.member3_id)
        self.assertEqual(Race.ZERG,    t1.race0)
        self.assertEqual(Race.UNKNOWN, t1.race1)
        self.assertEqual(Race.UNKNOWN, t1.race2)
        self.assertEqual(Race.UNKNOWN, t1.race3)

    def test_existent_2v2_random_team_is_updated_even_if_there_is_a_3v3_random_team_with_the_same_member(self):
        p1 = self.db.create_player(bid=301)

        t1 = self.db.create_team(mode=Mode.RANDOM_2V2,
                                 season=self.db.season,
                                 member0=p1,
                                 race0=Race.TERRAN)

        t2 = self.db.create_team(mode=Mode.RANDOM_3V3,
                                 season=self.db.season,
                                 member0=p1,
                                 race0=Race.RANDOM)

        self.process_ladder(mode=Mode.RANDOM_2V2, bid=301, race=Race.ZERG)

        self.assertEqual(2, len(Team.objects.all()))

        p1 = self.db.get(Player, bid=301)

        t1 = self.db.get(Team, id=t1.pk)
        self.assertEqual(Mode.RANDOM_2V2, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(None,  t1.member1_id)
        self.assertEqual(None,  t1.member2_id)
        self.assertEqual(None,  t1.member3_id)
        self.assertEqual(Race.ZERG,    t1.race0)
        self.assertEqual(Race.UNKNOWN, t1.race1)
        self.assertEqual(Race.UNKNOWN, t1.race2)
        self.assertEqual(Race.UNKNOWN, t1.race3)

        t2 = self.db.get(Team, id=t2.pk)
        self.assertEqual(Mode.RANDOM_3V3, t2.mode)
        self.assertEqual(p1.id, t2.member0_id)
        self.assertEqual(None,  t2.member1_id)
        self.assertEqual(None,  t2.member2_id)
        self.assertEqual(None,  t2.member3_id)
        self.assertEqual(Race.RANDOM,  t2.race0)
        self.assertEqual(Race.UNKNOWN, t2.race1)
        self.assertEqual(Race.UNKNOWN, t2.race2)
        self.assertEqual(Race.UNKNOWN, t2.race3)

    def test_existent_1v1_team_is_updated_on_league_change(self):
        p1 = self.db.create_player(bid=301)
        t1 = self.db.create_team(mode=Mode.TEAM_1V1,
                                 season=self.db.season,
                                 member0=p1,
                                 league=League.GOLD)

        self.process_ladder(mode=Mode.TEAM_1V1, league=League.SILVER, bid=301, race=Race.ZERG)

        self.assertEqual(1, len(Team.objects.all()))

        p1 = self.db.get(Player, bid=301)
        t1 = self.db.get(Team, id=t1.pk)
        self.assertEqual(1, len(Team.objects.all()))
        self.assertEqual(Mode.TEAM_1V1, t1.mode)
        self.assertEqual(p1.id, t1.member0_id)
        self.assertEqual(None,  t1.member1_id)
        self.assertEqual(None,  t1.member2_id)
        self.assertEqual(None,  t1.member3_id)
        self.assertEqual(League.SILVER, t1.league)
        self.assertEqual(Race.ZERG, t1.race0)
        self.assertEqual(Race.UNKNOWN, t1.race1)
        self.assertEqual(Race.UNKNOWN, t1.race2)
        self.assertEqual(Race.UNKNOWN, t1.race3)
