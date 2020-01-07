#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django
from django.db import connection

from tasks.base import Command
from common.utils import to_unix, utcnow
from lib import sc2
from main.battle_net import ApiLadder
from main.models import Ranking, get_db_name, Enums, Ladder, Mode, Cache


class Main(Command):

    def __init__(self):
        super().__init__("Repair a ranking by building it form scratch using all linked cache entries."
                         " WARNING: If this is the latest, you need to turn off fetching or it will be"
                         " overwritten.",
                         pid_file=True, stoppable=True)
        self.add_argument('--ranking', '-r', dest="ranking_id", type=int, default=None,
                          help="Ranking id to repair.")

    def run(self, args, logger):
        logger.info("NOTE: fetching needs to be turned off if repairing latest rank")

        ranking = Ranking.objects.get(pk=args.ranking_id)

        if ranking.status not in [Ranking.CREATED, Ranking.COMPLETE_WITH_DATA]:
            raise Exception("ranking with status %s can not be repaired" % ranking.status)

        # If last in season use all available ladders, not only those connected to ranking.
        last_in_season = Ranking.objects.filter(season=ranking.season).order_by('-id').first()
        if last_in_season == ranking:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM ("
                           "  SELECT DISTINCT ON (c.bid, c.region) c.id, c.updated FROM cache c JOIN ladder l"
                           "    ON c.bid = l.bid AND c.region = l.region"
                           "    WHERE l.strangeness = %s AND l.season_id = %s"
                           "    ORDER BY c.bid, c.region, c.updated DESC) s"
                           " ORDER by updated",
                           [Ladder.GOOD, ranking.season_id])
            cache_ids = [row[0] for row in cursor.fetchall()]
            cursor.execute("UPDATE cache SET ranking_id = NULL WHERE ranking_id = %s", [ranking.id])
        else:
            cache_ids = [c['id'] for c in ranking.sources.values('id').order_by('updated')]

        cpp = sc2.RankingData(get_db_name(), Enums.INFO)

        count = len(cache_ids)
        for i, id_ in enumerate(cache_ids, start=1):
            cache = Cache.objects.get(id=id_)
            self.check_stop()
            try:
                ladder = Ladder.objects.get(season=ranking.season, region=cache.region, bid=cache.bid)
            except Ladder.DoesNotExist:
                raise Exception("ladder region %s, bid %s missing in ladder table" %
                                (cache.region, cache.bid))

            if cache.ranking is None and cache.ladder is None:
                cache.ranking = ranking
                cache.save()
            elif cache.ranking != ranking:
                logger.info("cache %s was not included in ranking copying" % cache.id)
                cache.id = None
                cache.ladder = None
                cache.ranking = ranking
                cache.save()

            logger.info("adding cache %s, ladder %s, %d/%d" % (cache.id, ladder.id, i, count))

            team_size = Mode.team_size(ladder.mode)
            cpp.update_with_ladder(ladder.id,
                                   cache.id,
                                   ladder.region,
                                   ladder.mode,
                                   ladder.league,
                                   ladder.tier,
                                   ladder.version,
                                   ladder.season_id,
                                   to_unix(cache.updated),
                                   cache.updated.date().isoformat(),
                                   team_size,
                                   ApiLadder(cache.data).members_for_ranking(team_size))

        ranking.set_data_time(ranking.season, cpp)
        ranking.save()
        self.check_stop()
        cpp.save_data(ranking.id, ranking.season_id, to_unix(utcnow()))
        self.check_stop()
        cpp.save_stats(ranking.id, to_unix(utcnow()))

        return 0


if __name__ == '__main__':
    Main()()

