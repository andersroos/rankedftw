from random import randint, choice

from common.utils import merge_args, uniqueid, to_unix, utcnow
from main.battle_net import ApiLadder
from main.models import Race


def gen_member(**kwargs):
    """ Generate member as returned from ApiLadder and used by process_ladder. """
    return merge_args({"bid": randint(1, 1e6),
                       "realm": 1,
                       "name": uniqueid(length=12),
                       "clan": uniqueid(length=32),
                       "tag": uniqueid(length=6),
                       "join_time": int(to_unix(utcnow())),
                       "points": float(randint(0, 2000)),
                       "wins": randint(0, 200),
                       "mmr": randint(1000, 5000),
                       "losses": randint(0, 200),
                       "race": choice([Race.ZERG, Race.PROTOSS, Race.TERRAN, Race.RANDOM])
                       },
                      **kwargs)


def gen_ladder_data(members, team_size=1):
    """ Generate game data ladder data from members. """
    return {
        'league': 'unused',
        'team': [{
            'rating':          t[0]['mmr'],
            'join_time_stamp': t[0]['join_time'],
            'points':          t[0]['points'],
            'wins':            t[0]['wins'],
            'losses':          t[0]['losses'],
            'member': [{
                'character_link': {
                },
                'legacy_link': {
                    'name': m['name'] + '#123',
                    'realm': m['realm'],
                    'id':    m['bid'],
                },
                'clan_link': {
                    'clan_name': m['clan'],
                    'clan_tag':  m['tag'],
                },
                'played_race_count': [{
                    'count': 1,
                    'race': {'en_US': Race.name_by_ids[m['race']]},
                }],
            } for m in t],
        } for t in zip(*([iter(members)] * team_size))],
    }


def gen_api_ladder(members=None, team_size=1, url='http://fake-url', gd=True, **kwargs):
    """ Generate api ladder object from members and other data. Can generalte legacy data or gamedata version. """
    if members is None:
        members = [gen_member(**kwargs)]

    if gd:
        return ApiLadder(gen_ladder_data(members, team_size=team_size), url)
    else:

        # Skipping races for now, since it is not needed for current set of tests.
        # races["favoriteRaceP%d" % (i + 1)] = Race.key_by_ids[m['race']].upper()

        return ApiLadder({
            'ladderMembers': [{
                "points":        m['points'],
                "previousRank":  0,
                "wins":          m['wins'],
                "losses":        m['losses'],
                "highestRank":   0,
                "joinTimestamp": to_unix(m['join_time']),
                "character": {
                    "realm":        m['realm'],
                    "profilePath":  None,
                    "clanName":     m['clan'],
                    "id":           m['bid'],
                    "clanTag":      m['tag'],
                    "displayName":  m['name'],
                }
            } for m in members]
        }, url)
