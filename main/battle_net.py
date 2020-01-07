import os
from collections import namedtuple
import json
import urllib.request
import urllib.error
import urllib.parse
import socket
import re
import http.client

from logging import getLogger

from common.settings import config
from common.timer import Timer
from common.utils import utcnow, from_unix
from main.models import Region, Race, Mode, Version, League, Ladder


logger = getLogger('django')


API_KEY_AUTH = "apikey=%s" % config.API_KEY
ACCESS_TOKEN_AUTH = "access_token=%s" % config.ACCESS_TOKEN


# Last season currently available through the API.
LAST_AVAILABLE_SEASON = 28


NO_MMR = -32768


class LocalStatus(object):
    SOCKET_TIMEOUT = 600
    CONNECTION_REFUSED = 601
    INCOMPLETE_READ = 602
    BAD_STATUS_LINE = 603
    OS_ERROR = 604
    UNPARSABLE_JSON = 605
    DB_INCONSISTENCY = 606


LadderResponse = namedtuple("LadderResponse", ['status', 'api_ladder', 'fetch_time', 'fetch_duration'])
SeasonResponse = namedtuple("SeasonResponse", ['status', 'api_season', 'fetch_time', 'fetch_duration'])
LeagueResponse = namedtuple("LeagueResponse", ['status', 'api_league', 'fetch_time', 'fetch_duration'])


def get_bnet_profile_url_info(url):
    if "starcraft2.com" in url:
        # New style battle net profile  https://starcraft2.com/en-gb/profile/<region>/<realm>/<bid>

        match = re.match(r'.*/(\d+)/(\d+)/(\d+)', url)
        if not match:
            return None, None, None
        
        region = BnetClient.REGION_BY_IDS.get(match.group(1))
        realm = int(match.group(2))
        bid = int(match.group(3))
        
        if region is None:
            return None, None, None
        
        return region, realm, bid

    # Legacy style battle net profile.
    
    if "eu.battle.net" in url:
        region = Region.EU
    elif "us.battle.net" in url:
        region = Region.AM
    elif "kr.battle.net" in url:
        region = Region.KR
    elif "sea.battle.net" in url:
        region = Region.SEA
    elif "www.battlenet.com.cn" in url:
        region = Region.CN
    else:
        return None, None, None

    match = re.match(r'.*/(\d+)/(\d+)/.*', url)
    if not match:
        return None, None, None

    bid = int(match.group(1))
    realm = int(match.group(2))

    return region, realm, bid


class BnetClient(object):
    """ Bnet connection, is a class for easier mocking. """

    REGION_URL_PREFIXES = {
        Region.EU:  'https://eu.api.blizzard.com',
        Region.AM:  'https://us.api.blizzard.com',
        Region.KR:  'https://kr.api.blizzard.com',
        Region.CN:  'https://gateway.battlenet.com.cn',
    }
    
    REGION_IDS = {
        Region.EU:  '2',
        Region.AM:  '1',
        Region.KR:  '3',
        Region.CN:  '5',
        Region.SEA: '4',  # Unofficial but do not want sea profiles to crash.
    }

    REGION_BY_IDS = {v: k for k, v in REGION_IDS.items()}

    QUEUE_ID_MAJOR = {
        Version.WOL: 0,
        Version.HOTS: 100,
        Version.LOTV: 200,
    }

    QUEUE_ID_MINOR = {
        Mode.TEAM_1V1:   1,
        Mode.RANDOM_2V2: 2,
        Mode.TEAM_2V2:   2,
        Mode.RANDOM_3V3: 3,
        Mode.TEAM_3V3:   3,
        Mode.RANDOM_4V4: 4,
        Mode.TEAM_4V4:   4,
        Mode.ARCHON:     6,
    }

    TEAM_TYPE = {
        Mode.TEAM_1V1:   0,
        Mode.RANDOM_2V2: 1,
        Mode.TEAM_2V2:   0,
        Mode.RANDOM_3V3: 1,
        Mode.TEAM_3V3:   0,
        Mode.RANDOM_4V4: 1,
        Mode.TEAM_4V4:   0,
        Mode.ARCHON:     0,
    }

    def raw_get(self, url, timeout):
        return urllib.request.urlopen(url, timeout=timeout)

    def http_get(self, url, timeout, auth):
        """
        Get from url.

        :param url: url to get
        :param timeout: timeout in seconds
        :returns: <status code, raw data>, >= 600 are local client codes
        """
        url = urllib.parse.quote(url, safe='/:') + "?" + auth
        try:
            try:
                response = self.raw_get(url, timeout)
                try:
                    return response.getcode(), response.readall()
                except AttributeError:
                    return response.getcode(), response.read()
            except urllib.error.HTTPError as e:
                return e.getcode(), e.read()
            except urllib.error.URLError as e:
                if "timed out" in str(e):
                    return LocalStatus.SOCKET_TIMEOUT, None
                elif "Connection refused" in str(e):
                    return LocalStatus.CONNECTION_REFUSED, None
                else:
                    raise
        except socket.timeout:
            return LocalStatus.SOCKET_TIMEOUT, None
        except http.client.IncompleteRead:
            return LocalStatus.INCOMPLETE_READ, None
        except http.client.BadStatusLine:
            return LocalStatus.BAD_STATUS_LINE, None
        except OSError as e:
            return LocalStatus.OS_ERROR, None

    def http_get_json(self, url, timeout, auth):
        """
        Get and return json.
        If 200 and status code in json, code in json will be returned as status.
        If 200 and unparsable json, it will return <605, {'unparsable': '<content decoded as utf-8>'}>
        If non 200 and unparsable json, it will return <status, {'unparsable': '<content decoded as utf-8>'}>
        Non utf-8 response never happend.

        :returns: <status code, json data>
        """
        status, raw = self.http_get(url, timeout, auth)
        if raw is None:
            return status, {'unparsable': ''}

        try:
            data = raw.decode('utf-8')
        except AttributeError:
            data = raw

        try:
            json_data = json.loads(data)
        except ValueError:
            if status != 200:
                status = LocalStatus.UNPARSABLE_JSON
            json_data = {'unparsable': data}

        if status == 200:
            status = json_data.get('code', 200)  # Sometimes 200 status does not have code 200.

        return status, json_data

    def fetch_current_season(self, region, timeout=60):
        """
        Fetch current season information.

        :return: <status code, ApiSeasonInfo or None, fetch time, fetch duration>
        """
        url_prefix = self.REGION_URL_PREFIXES[region]
        region_id = self.REGION_IDS[region]
        
        url = f'{url_prefix}/sc2/ladder/season/{region_id}'
        timer = Timer()
        status, data = self.http_get_json(url, timeout, ACCESS_TOKEN_AUTH)
        return SeasonResponse(status, ApiSeason(data, url), utcnow(), timer.end())

    def fetch_league(self, region, season_id, version, mode, league, timeout=60):
        """
        Fetch league information.

        :return: <status code, ApiLeagueInfo or None, fetch time, fetch duration>
        """

        url_prefix = self.REGION_URL_PREFIXES[region]
        queue_id = self.QUEUE_ID_MAJOR[version] + self.QUEUE_ID_MINOR[mode]
        team_type = self.TEAM_TYPE[mode]

        url = f'{url_prefix}/data/sc2/league/{season_id}/{queue_id}/{team_type}/{league}'
        bid = league + team_type * 10 + queue_id * 100 + season_id * 100000
        timer = Timer()
        status, data = self.http_get_json(url, timeout, ACCESS_TOKEN_AUTH)
        return LeagueResponse(status, ApiLeague(data, url, bid), utcnow(), timer.end())

    def fetch_ladder(self, region, bid, timeout=60):
        """
        Fetch ladder from blizzard api.

        :return: <status code, ApiLadder or None, fetch time, fetch duration>
        """

        url_prefix = self.REGION_URL_PREFIXES[region]
        
        url = f"{url_prefix}/data/sc2/ladder/{bid}"
        timer = Timer()
        status, data = self.http_get_json(url, timeout, ACCESS_TOKEN_AUTH)
        al = ApiLadder(data, url)
        return LadderResponse(status, al, utcnow(), timer.end())


class ApiSeason(object):

    def __init__(self, data, url=None):
        if isinstance(data, str):
            self.data = json.loads(data)
        else:
            self.data = data
        self.url = url

    def season_id(self):
        return self.data['seasonId']

    def start_date(self):
        return from_unix(int(self.data['startDate'])).date()

    def to_text(self):
        if self.data:
            return json.dumps(self.data, indent=4)
        return None

    def __repr__(self):
        return f"ApiSeason(data={self.data!r}, url={self.url})"


class ApiLeague(object):

    def __init__(self, data, url=None, bid=None):
        if isinstance(data, str):
            self.data = json.loads(data)
        else:
            self.data = data
        self.url = url
        self.bid = bid

    def count(self):
        return sum([len(t.get('division', [])) for t in self.data.get('tier', [])])

    def tier_bids(self, tier):
        for t in self.data['tier']:
            if t['id'] == tier:
                return {d['ladder_id'] for d in t.get('division', [])}
        return set()

    def to_text(self):
        if self.data:
            return json.dumps(self.data, indent=4)
        return None

    def __repr__(self):
        return f"ApiLeague(bid={self.bid}, data={self.data!r}, url={self.url})"


class ApiLadder(object):

    def __init__(self, data, url=None):
        if isinstance(data, str):
            self.data = json.loads(data)
        else:
            self.data = data
        self.url = url

        # If is game data version
        self.gd = 'league' in self.data

    def to_text(self):
        if self.data:
            return json.dumps(self.data, indent=4)
        return None

    def is_empty(self):
        """ Return true if this ladder is empty, this is a buggy response. """
        empty = not bool(self.get())
        if empty and 'league' in self.data:
            self._log_empty_ladder()
        return empty

    def get(self):
        if self.gd:
            return self.data.get('team', [])
        else:
            return self.data.get('ladderMembers', [])

    def member_count(self):
        if self.gd:
            return sum(len(t.get('member', [])) for t in self.get())
        else:
            return len(self.get())

    def members_for_ranking(self, team_size):
        """ Return a list of ladder members enhanced for ranking by c++ code. Each ladder member is a dict. """
        members = []
        if self.gd:
            for t in self.get():
                ms = t.get('member', [])
                if not ms:
                    # Some ladders contain empty members.
                    self._log_empty_members()

                for m in ms:
                    if not m:
                        # Some ladders contain empty member.
                        self._log_empty_member()
                        continue

                    char = m.get('character_link', {})
                    legacy = m['legacy_link']
                    clan = m.get('clan_link', {})

                    # Is first race always latest played?
                    race = Race.id_by_keys[m.get('played_race_count', [{}])[0]
                                           .get('race', {}).get('en_US', 'unknown').lower()]

                    # Character_link is unusable for identifying a player since it does not have realm and names can
                    # change, have to use legacy link.
                    bid = legacy['id']
                    realm = legacy['realm']

                    mmr = t.get('rating', NO_MMR)
                    if mmr > 30000:
                        mmr = NO_MMR  # Mitigate Blizzard api bug.
                    self._log_bad_mmr(mmr == NO_MMR, bid, realm, self.url)

                    self._log_missing_char(not char, bid, realm)

                    member = {
                        'bid': bid,
                        'realm': realm,
                        'name': legacy.get('name', '').split('#')[0][:12],
                        'tag': clan.get('clan_tag', ''),
                        'clan': clan.get('clan_name', ''),
                        'race': race,
                        'mmr': mmr,
                        'points': t.get('points', 0),
                        'wins': t.get('wins', 0),
                        'losses': t.get('losses', 0),
                        'join_time': t.get('join_time_stamp', 0),
                    }
                    members.append(member)
        else:
            for i, m in enumerate(self.get()):
                c = m['character']
                members.append({
                    'bid': c['id'],
                    'realm': c['realm'],
                    'name': c['displayName'][:12],
                    'tag': c['clanTag'],
                    'clan': c['clanName'],
                    'race': Race.id_by_keys[m.get('favoriteRaceP%d' % (i % team_size + 1), 'unknown').lower()],
                    'mmr': NO_MMR,
                    'points': m['points'],
                    'wins': m['wins'],
                    'losses': m['losses'],
                    'join_time': m['joinTimestamp'],
                })

        return members

    def max_points(self):
        """ Returns the max points in this ladder. """
        members = self.get()
        if not members:
            return None
        if self.gd:
            return max(t.get('points', 0) for t in members)
        else:
            return max(m['points'] for m in members)
    
    def first_join(self):
        """ Returns the first join ladder time in  this ladder. """
        members = self.get()
        if not members:
            return None
        if self.gd:
            return from_unix(min(t.get('join_time_stamp', 0) for t in members))
        else:
            return from_unix(min(m['joinTimestamp'] for m in members))
    
    def last_join(self):
        """ Returns the last join ladder time in  this ladder. """
        members = self.get()
        if not members:
            return None
        if self.gd:
            return from_unix(max(t.get('join_time_stamp', 0) for t in members))
        else:
            return from_unix(max(m['joinTimestamp'] for m in members))

    def __repr__(self):
        return f"ApiLadder(data={self.data!r}, url={self.url})"

    #
    # Code for pre gd ladders only. Kept if recategorization of old ladders is needed.
    #

    def team_size(self):
        """ Return the team size of the first ladder entry. """
        if self.gd:
            raise Exception("not supported by gd")

        member = self.get()[0]
        if "favoriteRaceP4" in member:
            return 4
        elif "favoriteRaceP3" in member:
            return 3
        elif "favoriteRaceP2" in member:
            return 2
        elif "favoriteRaceP1" in member:
            return 1
        else:
            return 0

    def point_stats(self):
        """ Return <count, bad point count, max points > """
        if self.gd:
            raise Exception("not supported by gd")

        count = 0
        bad_count = 0
        max_points = 0
        for points in (m['points'] for m in self.get()):
            max_points = max(max_points, points)
            if points != round(points) and abs(points) > 1e-6:
                bad_count += 1
            count += 1
        return count, bad_count, max_points

    #
    # Logging of various problems with the new ladder, remove when fixed or workaround is good.
    #

    LOG_BAD = False  # Turn on and off logging of the errors. Try to turn on later to see if anything was fixed.

    MISSING = set()  # <bid, realm> for missing char missing from ladder
    BAD_MMR = set()  # <bid, realm, url> for bad mmr to see if they turn good at some point or is permanently bad.

    def _write_to_file(self, basename, message, dump_data=True):
        with open(os.path.join(config.LOG_DIR, basename), 'a') as f:
            f.write(message)
            f.write('\n')
            if dump_data:
                f.write(self.to_text())
                f.write('\n\n')

    def _log_empty_ladder(self):
        if self.LOG_BAD:
            self._write_to_file('api-fail-empty-ladder.txt', 'EMPTY LADDER FROM: %s at %s' % (self.url, utcnow()))

    def _log_empty_member(self):
        if self.LOG_BAD:
            self._write_to_file('api-fail-empty-member.txt', 'EMPTY MEMBER FROM: %s at %s' % (self.url, utcnow()))

    def _log_empty_members(self):
        if self.LOG_BAD:
            self._write_to_file('api-fail-empty-members.txt', 'EMPTY MEMBERS FROM: %s at %s' % (self.url, utcnow()))

    def _log_bad_mmr(self, bad, bid, realm, url):
        if self.LOG_BAD:
            basename = 'api-fail-bad-mmr.txt'
            key = (bid, realm, url)
            if bad:
                if key in self.BAD_MMR:
                    self._write_to_file(basename, 'STILL BAD %s   %s' % (key, utcnow()), dump_data=False)
                else:
                    self._write_to_file(basename, 'NEW BAD %s   %s' % (key, utcnow()), dump_data=False)
            else:
                if key in self.BAD_MMR:
                    self._write_to_file(basename, 'NOW GOOD %s   %s' % (key, utcnow()), dump_data=False)

    def _log_missing_char(self, missing, bid, realm):
        if self.LOG_BAD:
            basename = 'api-fail-missing-char.txt'
            key = (bid, realm)
            if missing:
                # Check if missing and found at the same time.
                for t in self.get():
                    for m in t['member']:
                        char = m.get('character_link', {})
                        legacy = m['legacy_link']
                        if char and (legacy['id'], legacy['realm']) == key:
                            # Disabled due to too common.
                            # self._write_to_file(basename, "BOTH MISSING AND FOUND %s IN %s   %s" %
                            #                     (key, self.url, utcnow()))
                            return

                self._write_to_file(basename, "MISSING %s IN %s   %s" % (key, self.url, utcnow()), dump_data=False)
                self.MISSING.add(key)

            else:
                if key in self.MISSING:
                    self._write_to_file(basename, "FOUND %s IN %s   %s" % (key, self.url, utcnow()), dump_data=False)


class ApiPlayer(object):

    def __init__(self, data, url=None):
        self.data = data
        self.url = url

    def get_season_id(self):
        return self.data.get('season', {}).get('seasonId', 0)

    def __repr__(self):
        return "ApiPlayer<data=%r>" % self.data


class ApiPlayerLadders(object):

    @staticmethod
    def get_bid_from_url(url):
        return int(re.match(".*/profile/(\\d+)/.*", url).group(1))
        
    def __init__(self, data, url=None):
        self.data = data
        self.url = url

    def to_text(self):
        if self.data:
            return json.dumps(self.data, indent=4)
        return None

    def curr(self):
        return self.data.get('currentSeason', [])

    def prev(self):
        return self.data.get('previousSeason', [])

    def refers(self, l_bid):
        """ Returns "curr"/"prev" if it refers, none if not. """
        if self.current_refers(l_bid):
            return "curr"
        if self.previous_refers(l_bid):
            return "prev"
        return None

    def current_refers(self, l_bid):
        return any((any((l.get('ladderId', 0) == l_bid for l in t.get('ladder', []))) for t in self.curr()))

    def previous_refers(self, l_bid):
        return any((any((l.get('ladderId', 0) == l_bid for l in t.get('ladder', []))) for t in self.prev()))

    def get_version_mode_league(self, l_bid, match):
        """ Returns <version, mode, league> for ladder bid in either curr or prev. """
        if match not in ('curr', 'prev'):
            raise Exception("match '%s' unexpected" % match)

        if match == 'prev':
            teams = self.prev()
        else:
            teams = self.curr()

        for team in teams:
            for ladder in team['ladder']:
                if ladder['ladderId'] == l_bid:
                    l = ladder
                    c = team['characters']
                    return self._get_version(l), self._get_mode(l, c), self._get_league(ladder)

        return Version.UNKNONW, Mode.UNKNONW, Ladder.UNKNONW

    @staticmethod
    def _get_mode(ladder, chars):
        team_size = len(chars)
        mmq = ladder['matchMakingQueue']
        if "SOLO" in mmq:
            return Mode.TEAM_1V1
        elif "TWOS" in mmq and "COMP" not in mmq:
            return Mode.TEAM_2V2 if team_size > 1 else Mode.RANDOM_2V2
        elif "THREES" in mmq:
            return Mode.TEAM_3V3 if team_size > 1 else Mode.RANDOM_3V3
        elif "FOURS" in mmq:
            return Mode.TEAM_4V4 if team_size > 1 else Mode.RANDOM_4V4
        elif "TWOS_COMP" in mmq:
            return Mode.ARCHON
        return Mode.UNKNOWN

    @staticmethod
    def _get_league(ladder):
        if ladder is None:
            return Ladder.UNKNOWN
        return League.id_by_keys[ladder['league'].lower()]

    @staticmethod
    def _get_version(ladder):
        if ladder is None:
            return Version.UNKNOWN
        mmq = ladder['matchMakingQueue'].strip()
        if "HOTS" in mmq:
            return Version.HOTS
        elif "LOTV" in mmq:
            return Version.LOTV
        elif mmq == "TWOS_COMP" or "_" not in mmq:
            return Version.WOL

        raise Exception("Could not get version from mmq '%s'." % mmq)

    def __repr__(self):
        return "ApiPlayerLadders<data=%r>" % self.data
