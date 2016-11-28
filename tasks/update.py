#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from tasks.base import Command, RegionsArgMixin
from main.update import countinously_update


class Main(RegionsArgMixin, Command):

    def __init__(self):
        super().__init__("Continously update current ladders and create new rankings for the current"
                         " season.",
                         pid_file=True, stoppable=True, pid_file_max_age=None)
        self.add_argument('--switch-hour', '-s', dest="switch_hour", type=int, default=10,
                          help="The hour when to switch to a new ranking.")

    def run(self, args, logger):
        countinously_update(regions=args.regions, check_stop=self.check_stop, switch_hour=args.switch_hour)

        return 0


if __name__ == '__main__':
    Main()()
