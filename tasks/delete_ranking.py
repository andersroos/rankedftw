#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from django.db import transaction

from main.delete import DataDeleter
from main.models import Ranking, Cache, RankingData, RankingStats
from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("Delete ranking and all cache data and ranking data linked to it, used for broken "
                         "rankings.",
                         pid_file=True, stoppable=False)
        self.add_argument('--delete', dest="delete", action='store_true', default=False,
                          help="If this is not set, deletes a dry run will be perfomed instead.")
        self.add_argument('--ranking', '-r', dest="ranking", default=0,
                          help="Ranking to delete.")

    def run(self, args, logger):
        data_deleter = DataDeleter(dry_run=not args.delete)
        data_deleter.delete_ranking(args.ranking)
        return 0


if __name__ == '__main__':
    Main()()
