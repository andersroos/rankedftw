#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from logging import getLogger
from common.logging import log_region
from common.utils import utcnow
from main.archive import DataArchiver
from tasks.base import Command


logger = getLogger('django')


class Main(Command):

    def __init__(self):
        super().__init__("", pid_file=False, stoppable=True)

    def run(self, args, logger):
        log_region('ALL')
        
        archiver = DataArchiver(now=utcnow())
        archiver.archive_unused_caches(check_stop=self.check_stop)
        
        return 0


if __name__ == '__main__':
    Main()()
