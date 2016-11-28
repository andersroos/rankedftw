#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from rocky.argparse import utcdatetime
from tasks.base import Command
from main.archive import DataArchiver
from common.utils import utcnow
from common.logging import log_region


class Main(Command):

    def __init__(self):
        super().__init__("Archive caches for old rankings to files and remove the from db to save space.",
                         pid_file=True, stoppable=True)
        self.add_argument('--now', dest="now", type=utcdatetime, default=utcnow(),
                          help="The date (YYYY-MM-DD HH:MM:SS) in utc to use for the processing.")

    def run(self, args, logger):
        log_region('ALL')

        archiver = DataArchiver(args.now)
        archiver.archive_rankings(check_stop=self.check_stop)

        return 0


if __name__ == '__main__':
    Main()()
