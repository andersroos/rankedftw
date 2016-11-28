#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("",
                         pid_file=False, stoppable=False)

    def run(self, args, logger):
        return 0


if __name__ == '__main__':
    Main()()
