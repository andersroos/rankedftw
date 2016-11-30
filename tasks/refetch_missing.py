#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from main.refetch import refetch_missing
from tasks.base import Command, RegionsArgMixin


class Main(RegionsArgMixin, Command):

    def __init__(self):
        super().__init__("Refetch missing ladders handle temporary battle net glitches.",
                         pid_file=True, stoppable=True)
        self.add_argument('--max-retries', '-m', dest="max_retries", default='60', type=int,
                          help="Only retry ladders that have less than 60 retries.")
        self.add_argument('--min-age', '-a', dest="min_age", default='24', type=int,
                          help="Only retry ladders that have been updated more than min-age hours ago.")
        self.add_argument('--force', '-f', dest="force", action='store_true', default=False,
                          help="Run even if too close to season break.")

    def run(self, args, logger):
        for region in args.regions:
            refetch_missing(region=region, max_retries=args.max_retries, min_age=args.min_age,
                            check_stop=self.check_stop)

        return 0


if __name__ == '__main__':
    Main()()
