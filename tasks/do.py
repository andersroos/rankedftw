#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
from csv import DictWriter
from logging import getLogger

import init_django

from main.battle_net import BnetClient
from main.models import Region, Version, Mode, League, Team, Race
from tasks.base import Command
from main.client import client


logger = getLogger('django')


def get_batch(offset):
    sort_key_id = 5
    version_id = Version.LOTV
    mode_id = Mode.TEAM_1V1
    limit = 10000

    data = client.get_ladder(key=sort_key_id, version=version_id, mode=mode_id, offset=offset, limit=limit)

    # Fetch information about teams from database.

    teams = data['teams']

    team_ids = {team["team_id"] for team in teams}
    team_mapping = {team.id: team
                    for team in
                    Team.objects
                    .filter(id__in=team_ids)
                    .all()
                    .select_related('member0', 'member1', 'member2', 'member3')}

    for tr in teams:
        t = team_mapping[tr["team_id"]]

        tr['mmr'] = '-' if tr['mmr'] < 0 else tr['mmr']

        tr["player_name"] = t.member0.name
        tr["player_tag"] = t.member0.tag
        tr["player_realm"] = t.member0.realm
        tr["player_id"] = t.member0.bid

    rows = []

    for team in teams:
        # dict_keys(['data_time', 'league', 'losses', 'm0_race', 'm1_race', 'm2_race', 'm3_race', 'mmr', 'points', 'region', 'team_id', 'tier', 'win_rate', 'wins', 'm0_id', 'm0_name', 'm0_tag'])
        
        row = dict(
            region=Region.key_by_ids[team['region']],
            league=League.key_by_ids[team['league']],
            race=Race.key_by_ids[team['m0_race']],
            mmr=team['mmr'],
            points=team['points'],
            wins=team['wins'],
            losses=team['losses'],
            player_name=team['player_name'],
            player_clan=team['player_tag'],
            player_id=team['player_id'],
            player_realm=team['player_realm'],
            data_fetch_timestamp=team['data_time'],
        )
        # print(row)
        rows.append(row)
    
    return rows


class Main(Command):

    def __init__(self):
        super().__init__("", pid_file=False, stoppable=True)

    def run(self, args, logger):
        with open('/tmp/ladder-data.csv', 'w') as f:
            writer = DictWriter(f, ['region', 'league', 'race', 'mmr', 'points', 'wins', 'losses', 'player_name',
                                    'player_clan', 'player_id', 'player_realm', 'data_fetch_timestamp'])
            writer.writeheader()
            
            offset = 0
            while True:
                self.check_stop()
                batch = get_batch(offset)
                offset += len(batch)
                if not batch:
                    break
                for row in batch:
                    writer.writerow(row)
    
            logger.info("done %d", offset)
        
        return 0


if __name__ == '__main__':
    Main()()
