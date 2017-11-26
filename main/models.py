# -*- coding: utf-8 -*-
from collections import Mapping
from datetime import datetime, time, timezone
from pprint import pprint

from django.conf import settings

from django.db import models
from django.db.models import Q, Max
from common.cache import caching
from common.utils import from_unix, classproperty


def get_db_name():
    db_name = settings.DATABASES.get('TEST', {}).get('NAME', '')
    if db_name:
        db_name = 'test_' + db_name
    if not db_name:
        db_name = settings.DATABASES['default'].get('NAME')
    return db_name


class EnumMeta(type):

    def __init__(self, name, bases, dct):
        super().__init__(name, bases, dct)

        v0_stat_count = 0
        v1_stat_count = 0

        for m in dct['mapping']:
            var, id, key, name, default, index, stat_version = m
            setattr(self, var,            id)
            setattr(self, var + "_ID",    id)
            setattr(self, var + "_KEY",   key)
            setattr(self, var + "_NAME",  name)
            setattr(self, var + "_INDEX", index)
            if default:
                self.DEFAULT = id
                self.DEFAULT_ID = id
                self.DEFAULT_KEY = key
            if stat_version == 0:
                v0_stat_count += 1
                v1_stat_count += 1
            elif stat_version == 1:
                v1_stat_count += 1
        setattr(self, "V0_STAT_COUNT", v0_stat_count)
        setattr(self, "V1_STAT_COUNT", v1_stat_count)

                
class EnumBase(object, metaclass=EnumMeta):
    
    # Columns: constant base, id, key, cased name, default
    mapping = [
    ]

    @classproperty
    @caching
    def name_by_ids(self):
        return {id: name for _, id, _, name, _, index, stat_version in self.mapping}

    @classproperty
    @caching
    def id_by_keys(self):
        return {key: id for var, id, key, name, default, index, stat_version in self.mapping}

    @classproperty
    @caching
    def key_by_ids(self):
        return {id: key for var, id, key, name, default, index, stat_version in self.mapping}

    @classproperty
    @caching
    def ids(self):
        return [id for var, id, key, name, default, index, stat_version in self.mapping]

    @classproperty
    @caching
    def stat_v0_ids(self):
        return [id for var, id, key, name, default, index, stat_version in self.mapping
                if stat_version is not None and stat_version <= 0]

    @classproperty
    @caching
    def stat_v1_ids(self):
        return sorted([id for var, id, key, name, default, index, stat_version in self.mapping
                       if stat_version is not None and stat_version <= 1])

    @classproperty
    @caching
    def keys(self):
        return [key for var, id, key, name, default, index, stat_version in self.mapping]

    @classproperty
    @caching
    def ranking_ids(self):
        """ The ids that are included in team rankings (for some enums special values for all and unknown are
        excluded, for others they are not). """
        return [id for var, id, key, name, default, index, stat_version in self.mapping if index is not None]


class Race(EnumBase):

    # Columns: constant base, id, key, cased name, default, index, included in stat version
    mapping = [
        ('UNKNOWN', -1, 'unknown', 'Unknown', False, 0, 0),
        ('ZERG',     0, 'zerg',    'Zerg',    True,  1, 0),
        ('PROTOSS',  1, 'protoss', 'Protoss', False, 2, 0),
        ('TERRAN',   2, 'terran',  'Terran',  False, 3, 0),
        ('RANDOM',   3, 'random',  'Random',  False, 4, 0),
    ]
    

class League(EnumBase):

    # Columns: constant base, id, key, cased name, default, index, included in stat version
    mapping = [
        ('ALL',        -2, 'all',         'All',         False, None, None),
        ('UNKNOWN',    -1, 'unknown',     'Unknown',     False, None, None),
        ('BRONZE',      0, 'bronze',      'Bronze',      False,    0,    0),
        ('SILVER',      1, 'silver',      'Silver',      False,    1,    0),
        ('GOLD',        2, 'gold',        'Gold',        False,    2,    0),
        ('PLATINUM',    3, 'platinum',    'Platinum',    False,    3,    0),
        ('DIAMOND',     4, 'diamond',     'Diamond',     False,    4,    0),
        ('MASTER',      5, 'master',      'Master',      False,    5,    0),
        ('GRANDMASTER', 6, 'grandmaster', 'Grandmaster', False,    6,    0),
    ]

    
class Region(EnumBase):

    # Columns: constant base, id, key, cased name, default, index, included in stat version
    mapping = [
        ('ALL',     -2, 'world',   'World',   True,  None, None),
        ('UNKNOWN', -1, 'unknown', 'Unknown', False, None, None),
        ('EU',       0, 'eu',      'EU',      False,    0,    0),
        ('AM',       1, 'am',      'AM',      False,    1,    0),
        ('KR',       2, 'kr',      'KR',      False,    2,    0),
        ('SEA',      3, 'sea',     'SEA',     False,    3,    0),
        ('CN',       4, 'cn',      'CN',      False,    4,    0),
    ]

    
class Version(EnumBase):

    # Columns: constant base, id, key, cased name, default, index, included in stat version
    # NOTE C++ team_rank finding code needs fixing when adding.
    mapping = [
        ('UNKNOWN', -1, 'unknown', 'Unknown', False, None, None),
        ('WOL',      0, 'wol',     'WoL',     False, 0,    0),
        ('HOTS',     1, 'hots',    'HotS',    False, 1,    0),
        ('LOTV',     2, 'lotv',    'LotV',    True,  2,    1),
    ]

    
class Mode(EnumBase):

    # Columns: constant base, id, key, cased name, default, index, included in stat version
    mapping = [
        ('UNKNOWN',    -1, 'unknown',    'Unknown',    False, None, None),
        ('TEAM_1V1',   11, '1v1',        '1v1',        True,     0,    0),
        ('TEAM_2V2',   20, 'team-2v2',   'Team 2v2',   False,    1,    0),
        ('RANDOM_2V2', 21, 'random-2v2', 'Random 2v2', False,    2,    0),
        ('TEAM_3V3',   30, 'team-3v3',   'Team 3v3',   False,    3,    0),
        ('RANDOM_3V3', 31, 'random-3v3', 'Random 3v3', False,    4,    0),
        ('TEAM_4V4',   40, 'team-4v4',   'Team 4v4',   False,    5,    0),
        ('RANDOM_4V4', 41, 'random-4v4', 'Random 4v4', False,    6,    0),
        ('ARCHON',     12, 'archon',     'Archon',     False,    7,    1),
    ]

    TEAM_SIZES = {11: 1, 20: 2, 21: 1, 30: 3, 31: 1, 40: 4, 41: 1, 12: 2, }
    
    @staticmethod
    def team_size(mode):
        return Mode.TEAM_SIZES[mode]


class Season(models.Model):
    """ Represents a ladder season. """

    # Min age between first join and fetch to categorize this ladder to anything else than NYD if lt 10 points or no
    # ap and lt 20 members.
    LADDER_AGE_BEFORE_CATEGORIZING_UNCERTAIN_LADDER = 14

    # Only do refetch past for seasons that closed this number of days before today. This is to make it not conflict
    # with the updating of the current season.
    REFETCH_PAST_MIN_DAYS_AFTER_SEASON_END = 3

    # Refetch past ladder until it is updated this long time after season end. This should be lower than
    # REFETCH_PAST_MIN_DAYS_AFTER_SEASON_END or it will refetch stuff several times.
    REFETCH_PAST_UNTIL_DAYS_AFTER_SEASON_END = 2

    # Refetch past ladder age limit. If ladder was not updated since this many days we give up, it will just
    # returns constant 600 or something.
    REFETCH_PAST_DAYS_AGE_LIMIT = 90

    class Meta:
        db_table = 'season'

    # Then start date of the season. If null this season is a placeholder for the coming season.
    start_date = models.DateField(null=True)

    # Then end date of the season. If null this season is ongoing.
    end_date = models.DateField(null=True)

    # The official year of this season.
    year = models.IntegerField()

    # The number within the year of this season.
    number = models.IntegerField()
    
    # The public name of the season.
    name = models.CharField(max_length=32)

    # The highest version of SC2 availbale in this season.
    version = models.IntegerField(null=False)

    def start_time(self, time_part=time.min):
        return datetime.combine(self.start_date, time_part).replace(tzinfo=timezone.utc)

    def end_time(self, time_part=time.max):
        return datetime.combine(self.end_date, time_part).replace(tzinfo=timezone.utc)

    @classmethod
    def get_current_season(self):
        """ Return the last season that is still open. """
        return self.objects.get(start_date__isnull=False, end_date__isnull=True)

    def active(self, date):
        """ Return true if the season was active this date. """
        return self.start_date <= date <= self.end_date

    @classmethod
    def get_active(self, date):
        """ Get the season that was active at date, None if no one was active. Will never return coming season. """
        try:
            return self.objects.get(Q(end_date__gte=date) | Q(end_date__isnull=True), start_date__lte=date)
        except self.DoesNotExist:
            return None

    def reload(self):
        return Season.objects.get(pk=self.pk)

    def is_open(self):
        return self.end_date is None

    def is_coming(self):
        return self.start_date is None

    def get_prev(self):
        """ Get the season before this. """
        return self.get_relative(-1)

    def get_next(self):
        """ Get the season after this. """
        return self.get_relative(1)

    def get_relative(self, diff):
        """ Get the season with relative id diff. """
        try:
            return Season.objects.get(pk=self.pk + diff)
        except Season.DoesNotExist:
            return None

    def near_start(self, dt, days=7):
        """ Return true if the date or datetime is near start (days days). """
        try:
            d = dt.date()
        except AttributeError:
            d = dt
        return abs((self.start_date - d).days) <= days

    def near_end(self, dt, days=7):
        """ Return true if the date or datetime is near end (days days). """
        try:
            d = dt.date()
        except AttributeError:
            d = dt
        return abs((self.end_date - d).days) <= days

    def __repr__(self):
        return "Season<id=%s, start=%s, end=%s>" % (self.id, self.start_date, self.end_date)

    __str__ = __repr__


class Cache(models.Model):
    """ This table is used to save the original content of http responses. """

    class Meta:
        db_table = 'cache'
        index_together = ("bid", "region", "type")

    # Thr URL the cache entry was retrieved from.
    url = models.CharField(max_length=256, null=False, db_index=True)

    # The Battle Net id for the entity in the cache.
    bid = models.IntegerField()

    # The type of data.
    LADDER = 0
    PLAYER = 1
    PLAYER_LADDERS = 2
    SEASON = 3  # bid is season_id
    LEAGUE = 4  # bid is concatenated number <season_id 2 dig><queue_id 3 dig><team_type 1 dig><league_id 1 dig>,
                # stupid but fast fix, this is used in bnet client and refetch past
    type = models.IntegerField(null=False)

    # Region, the region the data was fetched from.
    region = models.IntegerField(null=False)

    # The HTTP status of the response, generally only 200 and 404 are
    # cached.
    status = models.IntegerField(null=False)

    # The timestamp in UTC when the data was created in the databsae. Note that created may be after updated because
    # cache entries are copied when a new ranking is created.
    created = models.DateTimeField()

    # The last update time of the data in this row.
    updated = models.DateTimeField(db_index=True)

    # The "raw" data (the response body decoded as utf-8).
    data = models.TextField(null=True, default=None)

    # Number of retries for non 200 responses.
    retry_count = models.IntegerField(default=0)

    # The ranking that this cache is included in, ranking and ladder should never both be set.
    ranking = models.ForeignKey('Ranking', related_name='sources', null=True, on_delete=models.DO_NOTHING)

    # The ladder that this cache was contributing to categorize, ranking and ladder should never both be set.
    ladder = models.ForeignKey('Ladder', related_name="sources", null=True, on_delete=models.DO_NOTHING)

    def __repr__(self):
        return "Cache<id=%s, region=%s, bid=%s, type=%s, url=%s" \
               ", status=%s, retry_count=%s, created=%s, updated=%s>" % \
               (self.id, self.region, self.bid, self.type, self.url,
                self.status, self.retry_count, self.created, self.updated)

    __str__ = __repr__


class Ladder(models.Model):
    """ Remote ladder and the meta data associated with it. """

    class Meta:
        db_table = 'ladder'
        unique_together = ('region', 'bid')

    # The region this ladder belongs to.
    region = models.IntegerField()

    # The Battle Net id of this ladder.
    bid = models.IntegerField()

    # Is this ladder one of the strange ladders? A ladder is strange
    # if it has no related data and/or max points is less than 10 or if error code when fetched.
    GOOD = 0     # Have matching player ladders, can be categorized.
    NYD = 1      # Not yet determined. Not yet matching player, or too few points.
    STRANGE = 2  # Between seasons strange ladders, usually too many members and points that are fractions below 10.
    NOP = 3      # No players. Points seems legit but no players. Probably ok but unusable.
    MISSING = 4  # 404 or 500 when trying to fetch it.
    strangeness = models.IntegerField(default=NYD)

    # Creation time if this row.
    created = models.DateTimeField()
    
    # The last update time of this row.
    updated = models.DateTimeField(db_index=True)

    # The mode of ladder this is.
    mode = models.IntegerField(default=Mode.UNKNOWN)

    # The league (bronze, etc of this ladder)
    league = models.IntegerField(default=League.UNKNOWN)

    # The league tier (0, 1, 2, where 0 is best). Tiers was introduced season 28, prior all will have tier 0 (tier 0
    # is displayed as tier 1).
    tier = models.IntegerField(default=0)

    # The game version for this ladder (WoL, HotS)
    version = models.IntegerField(default=Version.UNKNOWN)

    # The ladder season this ladder belongs to. NULL means unknown.
    season = models.ForeignKey(Season, null=True, related_name='+', default=None, on_delete=models.DO_NOTHING)
    
    # The follwing fields are not strictly needed, but good to haves
    # from the actual ladder data.
    
    # Timestamp of the player that joined last (hopefully, the season
    # can be deduced from this).
    first_join = models.DateTimeField(null=True)

    # Timestamp of the player that joined first (hopefully, the season
    # can be deduced from this).
    last_join = models.DateTimeField(null=True)

    # Max points in the ladder.
    max_points = models.FloatField(null=True)

    # Member count in the ladder.
    member_count = models.IntegerField(null=True)

    @classmethod
    def max_good_bid(self, region):
        return Ladder.objects.filter(region=region, strangeness=Ladder.GOOD).aggregate(Max('bid'))['bid__max'] or 0

    def get_ladder_cache(self):
        return self.sources.get(type=Cache.LADDER)  # Should be one and only one.

    def get_player_ladders_cache(self):
        cs = list(self.sources.filter(type=Cache.PLAYER_LADDERS))  # Should be one or zero.
        if not cs:
            return None
        if len(cs) == 1:
            return cs[0]
        raise Exception("ladder %d has two player ladders, this should never happen" % self.id)

    @classmethod
    def strangeness_name(self, strangeness):

        return {self.GOOD: 'good',
                self.NYD: 'nyd',
                self.STRANGE: 'strange',
                self.NOP: 'nop',
                self.MISSING: 'missing'}[strangeness]

    def info(self):
        return "season %d, %s, %s, %s, tier %s, %s" % \
               (self.season.id, Mode.key_by_ids[self.mode], Version.key_by_ids[self.version],
                League.key_by_ids[self.league], self.tier, Ladder.strangeness_name(self.strangeness))

    def __repr__(self):
        return "Ladder<region=%s, bid=%s, strangeness=%s, season=%s" \
               ", mode=%s, legaue=%s, version=%s, max_points=%s, member_count=%s" \
               ", first_join=%s, last_join=%s, created=%s, updated=%s, id=%s>" % \
               (self.region, self.bid, self.strangeness, self.season_id,
                self.mode, self.league, self.version, self.max_points, self.member_count,
                self.first_join, self.last_join, self.created, self.updated, self.id)

    __str__ = __repr__
        
    
class Player(models.Model):
    """ A ladder player. The player name is updated at ladder processing. """
    
    class Meta:
        db_table = 'player'
        unique_together = ('bid', 'region', 'realm')
        
    # The region this ladder belongs to.
    region = models.IntegerField()
        
    # The Battle Net id of this player.
    bid = models.IntegerField()

    # The Realm of this player.
    realm = models.IntegerField(null=False)
    
    # The latest known name of this player.
    name = models.CharField(max_length=12, db_index=True)

    # The latest known clan tag of this player.
    tag = models.CharField(max_length=6, db_index=True)
    
    # The latest known clan of this player.
    clan = models.CharField(max_length=32, db_index=True)

    # The last season this player was active. May not have been active
    # with the mode and league below?
    season = models.ForeignKey(Season, null=True, related_name='+', default=None)

    # The preferred mode for this player (according to some smart algorithm). =>
    # Prefer mode 11, then ???
    mode = models.IntegerField(null=True)

    # The prefered league for this player (according to some smart agorithm).
    # Use leageu for prefered mode.
    league = models.IntegerField(null=True)
    
    # The prefered race for this player (according to some smart agorithm).
    # Use race for prefereed mode.
    race = models.IntegerField(null=True)
    
    def path(self):
        return '/profile/%d/%d/%s/' % (self.bid, self.realm, self.name)

    def __lt__(self, other):
        return self.id < other.id

    def __repr__(self):
        return "<id: %s, bid: %s, realm: %s, region: %s>" % (self.id, self.bid, self.realm, self.region)


class Team(models.Model):
    """ A ladder team. """

    class Meta:
        db_table = 'team'
        unique_together = ('member0', 'member1', 'member2', 'member3', 'mode')
        # Region not needed because players are regional and
        # designated by table pk. Mode is needed because TEAM_1v1 and
        # RANDOM_XvX is the same member info. Version is not
        # needed/wanted want to be able to track teams over version
        # switches and if someone plays several versions at once they
        # are to blame themselves.
        
    # The region this team belongs to.
    region = models.IntegerField()
        
    # The mode that this team is for.
    mode = models.IntegerField()

    # The last season this player was active. Warning! Due to players
    # leaving league this may be null for some (historic <= season 23)  teams.
    season = models.ForeignKey(Season, null=True, related_name='+', default=None)

    # The last known version of this team (vill prefer later versions
    # if conflicting). Warning! Due to players leaving league this may
    # be null for some (historic <= season 23) teams.
    version = models.IntegerField(null=True)
    
    # The last known league of this team (vill prefer league for later version).
    league = models.IntegerField()
    
    # Members, they have a canonical order by table pk of player.
    member0 = models.ForeignKey(Player, null=True, related_name='+', on_delete=models.DO_NOTHING)
    member1 = models.ForeignKey(Player, null=True, related_name='+', on_delete=models.DO_NOTHING)
    member2 = models.ForeignKey(Player, null=True, related_name='+', on_delete=models.DO_NOTHING)
    member3 = models.ForeignKey(Player, null=True, related_name='+', on_delete=models.DO_NOTHING)

    # Latest known race for all members in the team.
    race0 = models.IntegerField(default=Race.UNKNOWN)
    race1 = models.IntegerField(default=Race.UNKNOWN)
    race2 = models.IntegerField(default=Race.UNKNOWN)
    race3 = models.IntegerField(default=Race.UNKNOWN)

    def __repr__(self):
        return "<mode: %s, m0: %s, m1: %s, m2: %s, m3: %s>" % (self.mode, self.member0_id, self.member1_id,
                                                               self.member2_id, self.member3_id)

        
class Ranking(models.Model):
    """ Represents a full ranking of teams globally. """

    class Meta:
        db_table = 'ranking'
        
    # When this ranking was created, this may be a faked time in the past, but normally it is the actual creation
    # time. This is used to determine if a new ranking should be created or if we should update this one.
    created = models.DateTimeField()

    # Either the end of season or max_data_time whichever comes first. Used as display time on site for rankings an
    # stats. Also used to find out what data to delete (we want to keep rankings with an even spread). This should
    # be strictly increasing with later rankings (increasing ids).
    data_time = models.DateTimeField(db_index=True, null=False)

    # Min data_time (fetch time) of all included data.
    min_data_time = models.DateTimeField(null=False)

    # Max data_time (fetch time) of all included data.
    max_data_time = models.DateTimeField(null=False)

    # The season this ranking is restricted to.
    season = models.ForeignKey(Season, null=False, related_name='+', on_delete=models.DO_NOTHING)

    # The status of the ranking.
    CREATED = 0               # The ranking is created but not usable yet.
    COMPLETE_WITH_DATA = 1    # The ranking is usable and have all cache data present.
    COMPLETE_WITOUT_DATA = 2  # The ranking is usable but the cache data have been archived to save space.

    status = models.IntegerField(null=True)

    def set_data_time(self, season, cpp):
        """ Calculate and set data_times based off actual data and season. """

        self.min_data_time, self.max_data_time = [from_unix(d) for d in cpp.min_max_data_time()]
        if not self.min_data_time and not self.max_data_time:
            self.min_data_time = self.max_data_time = self.data_time = season.start_time()

        if season.is_open():
            self.data_time = self.max_data_time
        else:
            self.data_time = min(self.max_data_time, season.end_time())
            
    def __str__(self):
        return "RankingData<%s, %s>" % (self.id, self.data_time)

class RankingData(models.Model):
    """ The actual ranking data for the ranking. """

    class Meta:
        db_table = 'ranking_data'

    updated = models.DateTimeField()
    
    data = models.BinaryField(null=True, default=None)

    ranking = models.OneToOneField('Ranking', related_name='ranking_data', null=True)

    
class RankingStats(models.Model):
    """ Ranking statistics. """
    class Meta:
        db_table = 'ranking_stats'

    V0 = 0  # V0 is no longer used, all stats are migrated.

    V1 = 1
    V1_DATA_COUNT = Version.V1_STAT_COUNT * Region.V1_STAT_COUNT * League.V1_STAT_COUNT * Race.V1_STAT_COUNT
    V1_DATA_SIZE = 4
    V1_COUNT_INDEX = 0
    V1_WINS_INDEX = 1
    V1_LOSSES_INDEX = 2
    V1_POINT_INDEX = 3

    ranking = models.ForeignKey(Ranking, db_index=True)

    # The timestamp of when this data was saved in the database.
    updated = models.DateTimeField()
    
    data = models.TextField(null=True, default=None)

    @staticmethod
    def raw_v1_index(data_size, version_index, region_index, league_index, race_index):
        index = data_size * version_index * Region.V1_STAT_COUNT * League.V1_STAT_COUNT * Race.V1_STAT_COUNT
        index += data_size * region_index * League.V1_STAT_COUNT * Race.V1_STAT_COUNT
        index += data_size * league_index * Race.V1_STAT_COUNT
        index += data_size * race_index
        return index


def keys_to_str(d):
    return {str(k): keys_to_str(v) if isinstance(v, Mapping) else v for k, v in d.items()}


class Enums(object):
    """ An info structure of the contents of the enums to use in c++ and js. """

    INFO = {
        'stat': {
            RankingStats.V1: {
                'data_count': RankingStats.V1_DATA_COUNT,
                'data_size': RankingStats.V1_DATA_SIZE,
            },
        }
    }

    for clazz in Mode, Version, Region, League, Race:
        name = clazz.__name__.lower()
        INFO['%s_ranking_ids' % name] = clazz.ranking_ids
        INFO['%s_name_by_ids' % name] = clazz.name_by_ids
        INFO['%s_key_by_ids' % name] = clazz.key_by_ids
        INFO['stat'][RankingStats.V1]['%s_count' % name] = getattr(clazz, 'V1_STAT_COUNT')
        INFO['stat'][RankingStats.V1]['%s_ids' % name] = clazz.stat_v1_ids
        INFO['stat'][RankingStats.V1]['%s_indices' % name] = {id: i for i, id in enumerate(clazz.stat_v1_ids)}

    # In Javascript all keys have to be strings.
    INFO_JS = keys_to_str(INFO)
