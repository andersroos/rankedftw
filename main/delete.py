import sys

from django.db import transaction, connection
from logging import getLogger
from datetime import timedelta, datetime

from django.db.models import Q

from common.utils import utcnow, api_data_purge_date
from main.models import Ranking, Cache, RankingData, RankingStats, Ladder
from common.logging import log_context
from django.utils import timezone

logger = getLogger('django')


class BreakRun(Exception):

    pass


class DataDeleter(object):
    
    def __init__(self, dry_run=True):
        self.do_delete = not dry_run
        self.prefix = "DRY RUN NOT " if dry_run else ""

    def stop(self):
        pass
        
    @log_context(feature='del')
    def delete_old_rankings(self, keep_last=7):
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

            # Try to keep rankings with an interval of 7 days for the last year.
            last_kept = datetime(2000, 1, 1, 0, 0, 0).replace(tzinfo=timezone.utc)
            rrs.sort(key=lambda rr: rr[0].data_time)
            last_data_time = rrs[-1][0].data_time
            for rr in rrs:
                ranking = rr[0]
                if rr[1]:
                    last_kept = ranking.data_time
                else:
                    
                    # Keep every 7 days
                    if ranking.data_time - last_kept >= timedelta(days=7):
                    
                        # But if older than one year and archived. Keep every 4 weeks.
                        if last_data_time > ranking.data_time + timedelta(days=365)\
                                and ranking.status == Ranking.COMPLETE_WITOUT_DATA:
                            
                            if ranking.data_time - last_kept >= timedelta(days=28):
                                rr[1] = True
                                rr[2] = "new since 28 days, data from %s" % rr[0].data_time.date()
                                last_kept = rr[0].data_time
                            
                        else:
                            rr[1] = True
                            rr[2] = "new since 7 days, data from %s" % rr[0].data_time.date()
                            last_kept = rr[0].data_time
                    
            # Delete all rankings that has still is False
            rrs.sort(key=lambda rr: rr[0].id)
            for rr in rrs:
                if not rr[1]:
                    logger.info("%sremoving ranking %d because %s" % (self.prefix, rr[0].id, rr[2]))
                    if self.do_delete:
                        ranking_id = rr[0].id
    
                        cursor = connection.cursor()
                        cursor.execute("UPDATE cache SET ranking_id = NULL WHERE ranking_id = %s", [ranking_id])
    
                        Ranking.objects.filter(id=ranking_id).delete()
                else:
                    logger.info("keeping ranking %d beacuse %s" % (rr[0].id, rr[2]))

    @log_context(feature='del')
    def delete_old_cache_data(self, keep_days=30):
        """ Delete all cache data that is no longer linked from rankings or ladders but only if older than 30 days. """

        with transaction.atomic():
            objects = Cache.objects.filter(ladder__isnull=True, ranking__isnull=True, status=200,
                                           type__in=(Cache.LADDER, Cache.PLAYER, Cache.PLAYER_LADDERS, Cache.SEASON),
                                           updated__lt=utcnow() - timedelta(days=keep_days))

            count = objects.count()
            logger.info("%sremoving unreferenced %d cache objects" % (self.prefix, count))
            if self.do_delete:
                objects.delete()

    @log_context(feature='del')
    def agressive_delete_cache_data(self):
        """ Delete all cache data that is no longer linked from rankings or ladders or if it older than
         keep_days. """
    
        with transaction.atomic():
            query = Cache.objects.filter(
                Q(updated__lt=api_data_purge_date())
                | Q(ladder__isnull=True, ranking__isnull=True, type=Cache.LADDER)
                | Q(type__in=(Cache.PLAYER, Cache.PLAYER_LADDERS))
            )
        
            count = query.count()
            logger.info("%sremoving %d unreferenced cache objects" % (self.prefix, count))
            if self.do_delete:
                query.delete()

    @log_context(feature='del')
    def delete_ranking(self, pk):
        """ Delete ranking with pk, including ranking_data, ranking_stats and cache. """
        
        with transaction.atomic():
            ranking = Ranking.objects.get(pk=pk)
            
            # checking for linked ladder to rankings cache objects (should never happend)
            cache_ids = [c.id for c in
                         Cache.objects.raw("SELECT c.id FROM cache c WHERE ranking_id = %s AND ladder_id is not NULL",
                                           [ranking.id])]
            if cache_ids:
                raise Exception("rankings cache objects are tied to ladders: %s" % cache_ids)
    
            logger.info("%sdeleting %d ranking data" %
                        (self.prefix, RankingData.objects.filter(ranking=ranking).count()))
            if self.do_delete:
                RankingData.objects.filter(ranking=ranking).delete()
    
            logger.info("%sdeleting %d ranking stats" % (self.prefix, RankingStats.objects.filter(ranking=ranking).count()))
            if self.do_delete:
                RankingStats.objects.filter(ranking=ranking).delete()
    
            logger.info("%sdeleting %d caches" % (self.prefix, ranking.sources.count()))
            if self.do_delete:
                for c in ranking.sources.all():
                    c.delete()
    
            logger.info("%sdeleteing ranking %d" % (self.prefix, ranking.id))
            if self.do_delete:
                ranking.delete()

    @log_context(feature='del')
    def delete_ladders(self, keep_season_ids):
        """ Delete ladder data including cache, keep for seasons in keep_season_ids. """
        with transaction.atomic():
            
            logger.info(f"{self.prefix}deleting ladders keeping seasons {keep_season_ids}"
                        f" (seasons to keep depends on existing rankings so will be different for live run)")
            if self.do_delete:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM cache WHERE ladder_id in (SELECT id FROM ladder WHERE season_id NOT IN %s)",
                        [keep_season_ids]
                    )
                    cursor.execute(
                        "DELETE FROM ladder WHERE season_id NOT IN %s",
                        [keep_season_ids]
                    )
            