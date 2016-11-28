#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from main.battle_net import BnetClient
from main.fetch_new import fetch_new
from tasks.base import Command, RegionsArgMixin


class Main(RegionsArgMixin, Command):

    def __init__(self):
        super().__init__("Fetch new ladders, cache data, create new ladders and create new seasons.",
                         pid_file=True, stoppable=True)

    def run(self, args, logger):
        for region in args.regions:
            fetch_new(region=region, check_stop=self.check_stop, bnet_client=BnetClient())

        return 0


if __name__ == '__main__':
    Main()()
