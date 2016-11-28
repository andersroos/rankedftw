import sys

from django.db import transaction, connection
from logging import getLogger
from datetime import timedelta, datetime

from common.utils import utcnow
from main.models import Ranking, Cache
from common.logging import log_context
from django.utils import timezone

logger = getLogger('django')


class BreakRun(Exception):

    pass


class DataDeleter(object):
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    def stop(self):
        pass
        
    @log_context(feature='del')
    def delete_rankings(self, keep_last=7):
        """ Delete rankings for deletion and disconnect from cache, keep enough to make it interesting. """

        with transaction.atomic():

            rrs = list(Ranking.objects.select_for_update()
                       .filter(status__in=(Ranking.COMPLETE_WITH_DATA, Ranking.COMPLETE_WITOUT_DATA))
                       .all()
                       .order_by('-id'))
            # Prep list of <ranking, keep flag, reason>.
            rrs = [[rr, False, "remove is default, data from %s" % rr.data_time.date()] for rr in rrs]
            
            # Keep the last 7 rankings.
            for rr in rrs[:keep_last]:
                rr[1] = True
                rr[2] = "last 7, data from %s" % rr[0].data_time.date()

            # Keep the first ranking.
            rrs[-1][1] = True
            rrs[-1][2] = "first, data from %s" % rrs[-1][0].data_time.date()
                
            # Keep the last ranking of each season.
            season_id = 0
            for rr in rrs:
                if rr[0].season_id != season_id:
                    season_id = rr[0].season_id
                    rr[1] = True
                    rr[2] = "last from season %d, data from %s" % (season_id, rr[0].data_time.date())

            # Try to keep rankings with an interval of 7 days.
            last_kept = datetime(2000, 1, 1, 0, 0, 0).replace(tzinfo=timezone.utc)
            rrs.sort(key=lambda rr: rr[0].data_time)
            for rr in rrs:
                if rr[1]:
                    last_kept = rr[0].data_time
                else:
                    if rr[0].data_time - last_kept >= timedelta(days=7):
                        rr[1] = True
                        rr[2] = "new since 7 days, data from %s" % rr[0].data_time.date()
                        last_kept = rr[0].data_time

            # Delete all rankings that has still is False
            rrs.sort(key=lambda rr: rr[0].id)
            for rr in rrs:
                if not rr[1]:
                    logger.info("removing ranking %d because %s" % (rr[0].id, rr[2]))

                    if self.dry_run:
                        logger.info("DRY RUN NOT REMOVING %d rankings" %
                                    len(Ranking.objects.filter(id=rr[0].id)))
                    else:
                        ranking_id = rr[0].id

                        cursor = connection.cursor()
                        cursor.execute("UPDATE cache SET ranking_id = NULL WHERE ranking_id = %s", [ranking_id])

                        Ranking.objects.filter(id=ranking_id).delete()
                else:
                    logger.info("keeping ranking %d beacuse %s" % (rr[0].id, rr[2]))

    @log_context(feature='del')
    def delete_cache_data(self):
        """ Delete all cache data that is no longer linked from rankings or ladders but only if older than 30 days. """

        with transaction.atomic():
            objects = Cache.objects.filter(ladder__isnull=True, ranking__isnull=True, status=200,
                                           type__in=(Cache.LADDER, Cache.PLAYER, Cache.PLAYER_LADDERS, Cache.SEASON),
                                           updated__lt=utcnow() - timedelta(days=30))

            count = objects.count()
            if self.dry_run:
                logger.info("DRY RUN NOT REMOVING %d caches" % count)
            else:
                logger.info("removing unreferenced %d cache objects" % count)
                objects.delete()
