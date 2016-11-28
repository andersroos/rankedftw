#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from django.db import transaction
from main.models import Ranking, Cache, RankingData, RankingStats
from tasks.base import Command


class Main(Command):

    def __init__(self):
        super().__init__("Delete ranking and all cache data and ranking data linked to it, used for broken "
                         "rankings.",
                         pid_file=True, stoppable=False)
        self.add_argument('--delete', dest="delete", action='store_true', default=False,
                          help="If this is not set, deletes a dry run will be perfomed instead.")
        self.add_argument('--ranking', '-r', dest="ranking", default=0,
                          help="Ranking to delete.")

    def run(self, args, logger):
        with transaction.atomic():
            delete = args.delete
            prefix = "" if delete else "NOT "

            ranking = Ranking.objects.get(pk=args.ranking)

            logger.info("checking for linked ladder to rankings cache objects (should never happend)")
            cache_ids = [c.id for c in
                         Cache.objects.raw("SELECT c.id FROM cache c WHERE ranking_id = %s AND ladder_id is not NULL",
                                           [ranking.id])]
            if cache_ids:
                raise Exception("rankings cache objects are tied to ladders: %s" % cache_ids)

            logger.info("%sdeleting %d ranking data" % (prefix, RankingData.objects.filter(ranking=ranking).count()))
            if delete:
                RankingData.objects.filter(ranking=ranking).delete()

            logger.info("%sdeleting %d ranking stats" % (prefix, RankingStats.objects.filter(ranking=ranking).count()))
            if delete:
                RankingStats.objects.filter(ranking=ranking).delete()

            logger.info("%sdeleting %d caches" % (prefix, ranking.sources.count()))
            if delete:
                for c in ranking.sources.all():
                    c.delete()

            logger.info("%sdeleteing ranking %d" % (prefix, ranking.id))
            if delete:
                ranking.delete()

        return 0


if __name__ == '__main__':
    Main()()
