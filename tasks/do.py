#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
from pprint import pprint

import init_django

from logging import getLogger
from common.logging import log_region
from main.models import Ranking, get_db_name, Enums
from tasks.base import Command, RegionsArgMixin
from lib import sc2
from django.conf import settings


logger = getLogger('django')
sc2.set_logger(logger)


class Main(RegionsArgMixin, Command):

    def __init__(self):
        super().__init__("", pid_file=False, stoppable=True)

    def run(self, args, logger):
        log_region('ALL')

        rankings = Ranking.objects.order_by('-id')

        latest_time_by_region = {}
        latest_count_by_region = {}
        diff_time_by_region = {}
        
        get = sc2.Get(settings.DATABASES['default']['NAME'], Enums.INFO, 0)
        
        regions = {r for r in args.regions}
        
        for ranking in rankings:
            counts = get.games_played(ranking.id)
            if not latest_count_by_region:
                latest_time_by_region = {region: ranking.data_time for region in regions}
                latest_count_by_region = {region: counts.get(region, 0) for region in regions}
                print(f"start at {ranking.data_time}")
            else:
                for region in list(regions):
                    if latest_count_by_region[region] != counts.get(region):
                        diff_time_by_region[region] = ranking.data_time
                        regions.remove(region)
                        print(f"region {region} differs in ranking {ranking.id} at {ranking.data_time}")
                        
            if not regions:
                break

        for region in args.regions:
            age = latest_time_by_region[region] - diff_time_by_region[region]
            print(f"region {region} age {age.days} days")
            
        return 0


if __name__ == '__main__':
    Main()()
