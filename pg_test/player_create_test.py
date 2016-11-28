import aid.test.init_django_postgresql
from aid.test.data import gen_member

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from common.utils import utcnow
from main.models import Season, Region, Player, Mode, Team, Race


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

    def test_non_existent_player_is_created(self):
        self.process_ladder(bid=301,
                            realm=0,
                            name="player_name",
                            tag="EE",
                            clan="EE is our name")

        p = self.db.get(Player, bid=301)

        self.assertEqual(1, len(Player.objects.all()))
        self.assertEqual(0, p.realm)
        self.assertEqual(Region.EU, p.region)
        self.assertEqual("player_name", p.name)
        self.assertEqual("EE", p.tag)
        self.assertEqual("EE is our name", p.clan)

    def test_existing_player_is_updated_with_new_name_tag_clan_and_existing_other_player_is_not_touched(self):
        # See also whole file with player update tests.

        p1 = self.db.create_player(region=Region.EU,
                                   bid=301,
                                   realm=0,
                                   race=Race.ZERG,
                                   name="arne1",
                                   tag="arne1",
                                   clan="arne1")
        p2 = self.db.create_player(region=Region.EU,
                                   bid=302,
                                   realm=0,
                                   race=Race.ZERG,
                                   name="arne2",
                                   tag="arne2",
                                   clan="arne2")

        self.process_ladder(bid=301,
                            realm=0,
                            race=Race.ZERG,
                            name="player_name",
                            tag="EE",
                            clan="EE is our name")
        
        self.assertEqual(2, len(Player.objects.all()))

        p1 = self.db.get(Player, bid=301)
        self.assertEqual(0, p1.realm)
        self.assertEqual(Region.EU, p1.region)
        self.assertEqual("player_name", p1.name)
        self.assertEqual("EE", p1.tag)
        self.assertEqual("EE is our name", p1.clan)

        p2 = self.db.get(Player, bid=302)
        self.assertEqual(0, p2.realm)
        self.assertEqual(Region.EU, p2.region)
        self.assertEqual("arne2", p2.name)
        self.assertEqual("arne2", p2.tag)
        self.assertEqual("arne2", p2.clan)

    def test_player_occurs_in_several_teams_in_the_same_ladder_creates_one_player(self):
        # See our friend drake (bid 5305519, realm 1, region 1) in ladder 164930.

        self.db.create_ranking()
        self.process_ladder(mode=Mode.TEAM_2V2,
                            members=[
                                gen_member(bid=301,
                                           realm=0,
                                           name="arne1",
                                           race=Race.TERRAN),
                                gen_member(bid=302,
                                           realm=0,
                                           name="arne2",
                                           race=Race.TERRAN),
                                gen_member(bid=303,
                                           realm=0,
                                           name="arne3",
                                           race=Race.TERRAN),
                                gen_member(bid=301,
                                           realm=0,
                                           name="arne1",
                                           race=Race.TERRAN),
                            ])

        self.assertEqual(3, len(Player.objects.all()))

        p1 = self.db.get(Player, bid=301)
        p2 = self.db.get(Player, bid=302)
        p3 = self.db.get(Player, bid=303)

        self.assertEqual(2, len(Team.objects.all()))

        t1, t2 = self.db.filter(Team, member1_id__in=(p2.id, p3.id)).order_by('id')

        self.assertEqual(t1.member0_id, p1.id)
        self.assertEqual(t1.member1_id, p2.id)
        self.assertEqual(t2.member0_id, p1.id)
        self.assertEqual(t2.member1_id, p3.id)

        self.assertEqual('arne1', p1.name)
        self.assertEqual('arne2', p2.name)
        self.assertEqual('arne3', p3.name)
