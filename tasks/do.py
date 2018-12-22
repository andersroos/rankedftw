#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from main.battle_net import BnetClient
from main.models import Region, Version, Mode, League
from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("", pid_file=False, stoppable=False)

    def run(self, args, logger):

        client = BnetClient()

        season_id = 38

        region = Region.EU
        
        logger.info(Region.key_by_ids[region])
        
        logger.info(client.fetch_current_season(region))
            
        logger.info(client.fetch_league(region, season_id, Version.LOTV, Mode.TEAM_1V1, League.MASTER))
        
        logger.info(client.fetch_ladder(region, 210556))
        
        return 0


if __name__ == '__main__':
    Main()()
