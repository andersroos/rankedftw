from datetime import timedelta
from time import perf_counter

from django.db import transaction
from logging import getLogger

from django.db.models import Min

from main.fetch import update_ladder_cache, fetch_new_in_region
from main.models import Season, Cache, Ladder, Ranking, Enums, get_db_name, Region
from main.battle_net import BnetClient
from common.utils import utcnow, to_unix
from common.logging import log_context, LogContext
from lib import sc2


logger = getLogger('django')
sc2.set_logger(logger)


@log_context(feature='missing')
def refetch_missing(region=None, max_retries=None, min_age=None, check_stop=lambda: None, bnet_client=None):
    """ Refetch missing ladders. Note that these ladders will not be added to any ranking if passed current season. """

    bnet_client = bnet_client or BnetClient()

    # Find the latest ladders.

    bids = list(Cache.objects
                .values_list('bid', flat=True)
                .filter(region=region,
                        type=Cache.LADDER,
                        retry_count__lt=max_retries,
                        ladder__strangeness=Ladder.MISSING)
                .exclude(updated__gt=utcnow() - timedelta(hours=min_age))
                .order_by('-bid')
                .all()[:800])

    bid_count = len(bids)
    logger.info("refetching %d (max 800) non 200 ladders" % bid_count)

    for count, bid in enumerate(bids, start=1):
        check_stop()

        logger.info("refetching missing ladder bid %d, %d/%d" % (bid, count, bid_count))
        res = bnet_client.fetch_ladder(region=region, bid=bid)
        al = res.api_ladder

        if res.status == 503:
            logger.warning("got status 503, breaking for this region")
            return

        with transaction.atomic():

            cache = Cache.objects.get(region=region, bid=bid, type=Cache.LADDER)
            ladder = cache.ladder

            cache.status = res.status
            cache.data = al.to_text()
            cache.updated = res.fetch_time

            ladder.updated = res.fetch_time

            if res.status != 200:
                cache.retry_count += 1
            else:
                ladder.strangeness = Ladder.GOOD
                ladder.max_points = al.max_points()
                ladder.first_join = al.first_join()
                ladder.last_join = al.last_join()
                ladder.member_count = al.member_count()
                cache.retry_count = 0

            cache.save()
            ladder.save()

            if ladder.strangeness == Ladder.GOOD:
                logger.info("ladder %s no longer missing, saved as %s" % (ladder.id, ladder.info()))

            else:
                logger.info("status is %d, updated cache, retry_count %d" % (cache.status, cache.retry_count))


def refetch_past_season(season, now, check_stop, bnet_client):
    """ Refetch ladders for past seasons. """

    start = perf_counter()

    need_refetch_limit = now - timedelta(days=Season.REFETCH_PAST_REFRESH_WHEN_OLDER_THAN_DAYS)

    with transaction.atomic():
        ranking = Ranking.objects.filter(season=season).order_by('-data_time').first()
        if ranking is None:
            logger.warning(f"season {season.id} has no ranking to check refetch past for, this is strange, skipping")
            return

        ladders_query = Ladder.objects.filter(season=season, strangeness=Ladder.GOOD)

        last_updated = ladders_query.aggregate(Min('updated'))['updated__min']

        if need_refetch_limit < last_updated:
            logger.info(f"skipping refetch of season {season.id}, it was refetched {last_updated.date()}")
            return

        ladders = list(ladders_query.filter(updated__lt=need_refetch_limit))

        ladders_count = ladders_query.count()

        logger.info(f"{len(ladders)} (of {ladders_count}) to refetch for season {season.id}")

    # if not ladders:
    #     return

    # This is kind of bad but since c++ works in it's own db connection we can't fetch ladders and update
    # ranking in same transaction, which in turn means that if the code fails here ranking needs to be repaired.
    # TODO Move updating of cache to cpp? How is this done in update?
    
    cpp = sc2.RankingData(get_db_name(), Enums.INFO)
    cpp.load(ranking.id)

    fetch_time = 0

    try:
        for i, ladder in enumerate(ladders, start=1):
            check_stop()

            with transaction.atomic(), LogContext(region=Region.key_by_ids[ladder.region]):

                status, api_ladder, fetch_time, fetch_duration = \
                    bnet_client.fetch_ladder(ladder.region, ladder.bid, timeout=20)

                logger.info("fetched %s got %d in %.2fs, %s (%d/%d)" %
                            (api_ladder.url, status, fetch_duration, ladder.info(), i, len(ladders)))

                if status == 503:
                    logger.warning("got 503, skipping refetch past for rest of this season")
                    raise SystemExit()

                if status != 200:
                    logger.info("refetching %d returned %d, skipping ladder" % (ladder.id, status))
                    continue

                update_ladder_cache(cpp, ranking, ladder, status, api_ladder, fetch_time)

                logger.info("saved updated ladder %d and added data to ranking %d" % (ladder.id, ranking.id))

    except SystemExit:
        pass

    except Exception as e:
        raise Exception("failure while refetching past, you will need to repair ranking %d:" % ranking.id) from e

    if fetch_time:
        logger.info("saving ranking data and ranking stats for ranking %d" % ranking.id)
        cpp.save_data(ranking.id, ranking.season_id, to_unix(utcnow()))
        cpp.save_stats(ranking.id, to_unix(utcnow()))
        ranking.set_data_time(season, cpp)
        ranking.save()
    else:
        logger.info("skipping save of ranking data and ranking stats for ranking %d, nothing changed" % ranking.id)
        
    logger.info(f"completed refetch of season {season.id} in {int(perf_counter() - start)} seconds")
    

@log_context(feature='past', region='ALL')
def refetch_past_seasons(check_stop=lambda: None, bnet_client=None, now=None, skip_fetch_new=False):

    bnet_client = bnet_client or BnetClient()
    now = now or utcnow()

    # Wait for this date before refetching season.
    season_end_limit = now - timedelta(days=Season.REFETCH_PAST_MIN_DAYS_AFTER_SEASON_END)

    # Fetch new for a while after season close to make sure we got all ladders. Since we don't save non 200 leagues
    # we can still miss ladders here, but unlikely. There is no point in continuing after need_refetch_limit since they
    # will not be picked up in the ranking anyway.
    prev_season = Season.get_current_season().get_prev()
    need_refetch_limit = prev_season.end_time() + timedelta(days=Season.REFETCH_PAST_UNTIL_DAYS_AFTER_SEASON_END)
    if not skip_fetch_new and prev_season.end_time() < now <= need_refetch_limit:
        for region in Region.ranking_ids:
            fetch_new_in_region(check_stop, bnet_client, prev_season, region)

    # Refetch all past seasons, skip if refreshed recently. Skip seasons before 28 since they are not available in
    # the api.
    for season in Season.objects.filter(id__gte=28, end_date__lt=season_end_limit).order_by('-id'):
        refetch_past_season(season, now, check_stop, bnet_client)
        check_stop()

