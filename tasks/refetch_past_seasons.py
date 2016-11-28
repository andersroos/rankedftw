#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from main.refetch import refetch_past_seasons
from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("Refetch past seasons if more ladders has been added or if all ladders has not"
                         " been refetched before end of season. Will update the ranking and ranking stats."
                         " Will not run for a season if closed to recently to prevent it from colliding"
                         " with the current ranking. It will also fetch leagues for last season."
                         " NOTE: It will not handle ladders that is no longer"
                         " in the season (in case you think fixing bad seasons for old ladders will work).",
                         pid_file=True, stoppable=True)

    def run(self, args, logger):
        refetch_past_seasons(check_stop=self.check_stop)

        return 0


if __name__ == '__main__':
    Main()()
