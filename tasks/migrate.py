#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from common.utils import to_unix, utcnow
from main.models import Ranking, get_db_name, Enums
from tasks.base import Command
from lib import sc2


class Main(Command):

    def __init__(self):
        super().__init__("Speciality migrations outside migrations.",
                         pid_file=False, stoppable=False)

    def run(self, args, logger):

        cpp = sc2.RankingData(get_db_name(), Enums.INFO)

        for ranking in Ranking.objects.filter(season_id__gte=28):
            cpp.load(ranking.id)
            cpp.save_data(ranking.id, ranking.season_id, to_unix(utcnow()))
            cpp.save_stats(ranking.id, to_unix(utcnow()))

        return 0


if __name__ == '__main__':
    Main()()
