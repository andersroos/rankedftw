#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
from csv import DictWriter
from logging import getLogger

import init_django

from tasks.base import Command


logger = getLogger('django')


class Main(Command):

    def __init__(self):
        super().__init__("", pid_file=False, stoppable=True)

    def run(self, args, logger):
        
        return 0


if __name__ == '__main__':
    Main()()
