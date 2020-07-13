#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from common.logging import log_region
from main.delete import DataDeleter
from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("Delete rankings marked for deletion and unused cache data.",
                         pid_file=True, stoppable=False)
        self.add_argument('--dry-run', dest="dry_run", action='store_true', default=False,
                          help="Print deletes do NOT PERFORM them.")

    def run(self, args, logger):
        log_region('ALL')

        data_deleter = DataDeleter(dry_run=args.dry_run)
        data_deleter.delete_old_rankings()
        data_deleter.delete_old_cache_data()

        return 0


if __name__ == '__main__':
    Main()()
