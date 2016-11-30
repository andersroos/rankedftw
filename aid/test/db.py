import json
from logging import getLogger

from aid.test.data import gen_ladder_data
from common.utils import merge_args, uniqueid, to_unix, utcnow
from random import randint
from django.db import connection

from lib import sc2
from main.models import RankingData, Cache, Ranking, Team, Player, Ladder, Season, Version, Region, League, \
    Mode, Race, Enums
from main.models import RankingStats

logger = getLogger('django')
sc2.set_logger(logger)


class Db(object):
    """ Helper class to create test data in db. """

    def __init__(self):
        self.db_name = connection.settings_dict['NAME']
        print(self.db_name)
        self.team = None
        self.cache = None
        self.player = None
        self.season = None
        self.ladder = None
        self.ranking = None
        self.ranking_data = None
        self.default_ranking_data__data = {}
        self.clear_defaults()

    def clear_defaults(self):
        self.default_ranking_data__data = {}

    @staticmethod
    def filter(klass, *args, **kwargs):
        return klass.objects.filter(*args, **kwargs)

    @staticmethod
    def count(klass, *args, **kwargs):
        return klass.objects.filter(*args, **kwargs).count()

    @staticmethod
    def get(klass, *args, **kwargs):
        return klass.objects.get(*args, **kwargs)

    @staticmethod
    def objects(klass):
        return klass.objects

    @staticmethod
    def all(klass):
        return klass.objects.all()

    @staticmethod
    def execute(sql):
        cursor = connection.cursor()
        cursor.execute(sql)
        return cursor

    def delete_all(self, keep=None, delete=None):
        for d in (delete or [RankingData, RankingStats, Cache, Ranking, Team, Player, Ladder, Season]):
            if d not in (keep or []):
                if d == Ranking:
                    cursor = connection.cursor()
                    cursor.execute("update cache set ranking_id = NULL")
                if d == Ladder:
                    cursor = connection.cursor()
                    cursor.execute("update cache set ladder_id = NULL")
                self.all(d).delete()

    def create_season(self, **kwargs):
        kwargs = merge_args({'id': 16,
                             'start_date': '2013-11-11',
                             'end_date': '2014-01-03',
                             'name': '2013 Season 6',
                             'year': 2013,
                             'number': 6,
                             'version': Version.HOTS},
                            **kwargs)
        try:
            self.get(Season, id=kwargs['id'])
            raise AssertionError("Season with id %d already exists." % kwargs['id'])
        except Season.DoesNotExist:
            pass
        self.season = Season(**kwargs)
        self.season.save()
        return self.season

    def create_cache(self, type=Cache.LADDER, members=None, **kwargs):
        data = kwargs.pop('data', None)
        if data is None and members is not None:
            data = gen_ladder_data(members)

        kwargs = merge_args({'bid': randint(1, 1e6),
                             'url': 'http://bnet/' + uniqueid(10),
                             'type': type,
                             'region': Region.EU,
                             'created': utcnow(),
                             'updated': utcnow(),
                             'status': 200,
                             'retry_count': 0},
                            **kwargs)
        kwargs['data'] = json.dumps(data)
        
        self.cache = Cache(**kwargs)
        self.cache.save()
        return self.cache

    def create_ladder(self, **kwargs):
        kwargs = merge_args({'bid': 1,
                             'region': Region.EU,
                             'strangeness': Ladder.GOOD,
                             'league': League.GOLD,
                             'tier': 0,
                             'version': Version.HOTS,
                             'mode': Mode.TEAM_1V1,
                             'season': self.season,
                             'first_join': utcnow(),
                             'last_join': utcnow(),
                             'created': utcnow(),
                             'updated': utcnow(),
                             'max_points': 20},
                            **kwargs)

        self.ladder = Ladder(**kwargs)
        self.ladder.save()
        return self.ladder
    
    def create_player(self, **kwargs):
        kwargs = merge_args({'bid': randint(0, 1e9),
                             'region': Region.EU,
                             'realm': 0,
                             'mode': Mode.TEAM_1V1,
                             'season': self.season,
                             'race': Race.ZERG,
                             'name': uniqueid(12),
                             'clan': uniqueid(32),
                             'tag': uniqueid(6)},
                            **kwargs)
        self.player = Player(**kwargs)
        self.player.save()
        return self.player

    def create_team(self, **kwargs):
        kwargs = merge_args(dict(region=Region.EU,
                                 mode=Mode.TEAM_1V1,
                                 season=self.season,
                                 version=Version.HOTS,
                                 league=League.GOLD,
                                 member0=self.player,
                                 member1=None,
                                 member2=None,
                                 member3=None,
                                 race0=Race.ZERG,
                                 race1=Race.UNKNOWN,
                                 race2=Race.UNKNOWN,
                                 race3=Race.UNKNOWN),
                            **kwargs)

        self.team = Team(**kwargs)
        self.team.save()
        return self.team

    def create_teams(self, count=1, **kwargs):
        teams = []
        for i in range(count):
            self.create_player(name="%s-%d" % (uniqueid(8), i))
            teams.append(self.create_team(**kwargs))
        return teams

    def get_teams_by_member0_bids(self, *bids, mode=Mode.TEAM_1V1):
        tids = []
        for bid in bids:
            p = self.get(Player, bid=bid)
            tids.append(self.get(Team, member0=p, mode=mode).id)
        return tids

    def create_ranking(self, **kwargs):
        kwargs = merge_args(dict(created=utcnow(),
                                 data_time=utcnow(),
                                 min_data_time=utcnow(),
                                 max_data_time=utcnow(),
                                 status=Ranking.COMPLETE_WITH_DATA,
                                 season=self.season),
                            **kwargs)

        self.ranking = Ranking.objects.create(**kwargs)
        return self.ranking

    def _default_team_rank(self, team_rank):
        """ Update a team_rank dict with defaults. """
        for k, v in self.default_ranking_data__data.items():
            team_rank.setdefault(k, v)
        team_rank.setdefault("team_id", self.team.id)
        team_rank.setdefault("data_time", to_unix(self.ranking.data_time))
        team_rank.setdefault("version", Version.HOTS)
        team_rank.setdefault("region", Region.EU)
        team_rank.setdefault("mode", Mode.TEAM_1V1)
        team_rank.setdefault("league", League.GOLD)
        team_rank.setdefault("tier", 0)
        team_rank.setdefault("ladder_id", self.ladder.id)
        team_rank.setdefault("join_time", to_unix(self.ranking.data_time))
        team_rank.setdefault("source_id", self.cache.id)
        team_rank.setdefault("mmr", 1000)
        team_rank.setdefault("points", 100.0)
        team_rank.setdefault("wins", 10)
        team_rank.setdefault("losses", 10)
        team_rank.setdefault("race0", Race.ZERG)
        team_rank.setdefault("race1", Race.UNKNOWN)
        team_rank.setdefault("race2", Race.UNKNOWN)
        team_rank.setdefault("race3", Race.UNKNOWN)
        team_rank.setdefault("ladder_rank", 1)
        team_rank.setdefault("ladder_count", 1)
        team_rank.setdefault("league_rank", 1)
        team_rank.setdefault("league_count", 1)
        team_rank.setdefault("region_rank", 1)
        team_rank.setdefault("region_count", 1)
        team_rank.setdefault("world_rank", 1)
        team_rank.setdefault("world_count", 1)

    def create_ranking_data(self, **kwargs):
        kwargs = merge_args(dict(ranking=self.ranking,
                                 updated=utcnow()), kwargs)
        data = kwargs.pop('data', [])

        for team_rank in data:
            self._default_team_rank(team_rank)
            kwargs['ranking'].sources.add(self.get(Cache, pk=team_rank['source_id']))

        self.ranking_data = RankingData.objects.create(**kwargs)
        sc2.save_ranking_data_raw(self.db_name, kwargs['ranking'].id, 0, data, True)
        return self.ranking_data

    def update_ranking_stats(self, ranking_id=None):
        """ Will build ranking stats based of the ranking by calling c++. """
        if ranking_id is None: ranking_id = self.ranking.id
        cpp = sc2.RankingData(self.db_name, Enums.INFO)
        cpp.load(ranking_id)
        cpp.save_stats(ranking_id, to_unix(utcnow()))
        cpp.release()
