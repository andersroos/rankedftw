#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from django.db import transaction

from common.utils import utcnow
from main.archive import DataArchiver
from main.delete import DataDeleter
from main.models import Ranking
from main.purge import purge_player_data
from tasks.base import Command


class Main(Command):
    
    def __init__(self):
        super().__init__("Delete ranking and all cache data and ranking data linked to it, used for broken "
                         "rankings.",
                         pid_file=True, stoppable=False)
        self.add_argument('--delete', dest="delete", action='store_true', default=False,
                          help="If this is not set, deletes a dry run will be performed instead.")
        self.add_argument('--keep-rankings', '-r', dest="keep_rankings", default=None,
                          help="Comma separated list of rankings to keep.")
    
    def run(self, args, logger):
    
        keep_ids = (int(id) for id in args.keep_rankings.split(","))

        with transaction.atomic():
            remove_ids = [r.id for r in Ranking.objects.exclude(id__in=keep_ids)]
    
        data_deleter = DataDeleter(dry_run=not args.delete)
        data_archiver = DataArchiver(utcnow(), remove=True)
        
        # Remove rankings.
        
        for remove_id in remove_ids:
            data_deleter.delete_ranking(remove_id)
        
        # Archive all rankings except the last.
        if args.delete:
            rankings = Ranking.objects.order_by("-id")[1:]
            for ranking in rankings:
                logger.info(f"archiving ranking {ranking.id}")
                data_archiver.archive_ranking(ranking, self.check_stop)
        else:
            logger.info("DRY RUN no archiving of rankings")
            
        # Delete ladders that are no longer needed.
        
        keep_season_ids = {r.season_id for r in Ranking.objects.all()}
        data_deleter.delete_ladders(tuple(keep_season_ids))
        
        # Delete cache data that is unused.
        
        data_deleter.agressive_delete_cache_data()

        # Purge players and teams.

        if args.delete:
            purge_player_data(check_stop=self.check_stop)
        else:
            logger.info("DRY RUN no purge player data")
        
        return 0


if __name__ == '__main__':
    Main()()
