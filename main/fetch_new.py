from datetime import timedelta
from logging import getLogger, INFO, WARNING
from django.db import transaction

from common.logging import log_context
from common.utils import utcnow
from main.fetch import fetch_new_in_region
from main.models import Version, Season, Ranking, Cache, Region

logger = getLogger('django')


def create_new_season(current_season, end_date):

    # New season.
    logger.info("detected season change")

    # New season date is not super important, ladders around break will end up in correct season, so
    # set it to today + 1 day.
    season = current_season

    season.end_date = end_date
    season.save()
    logger.info("set end date %s on season %d" % (season.end_date, season.id))

    next_season = season.get_next()
    next_season.start_date = end_date + timedelta(days=1)
    next_season.year = next_season.start_date.year
    next_season.number = 1 if next_season.year != season.year else season.number + 1
    next_season.name = "%d Season %d" % (next_season.year, next_season.number)
    next_season.save()
    logger.info("set start data %s, year, name and number on season %d" %
                (next_season.start_date, next_season.id))

    next_next_season = Season(id=next_season.id + 1,
                              start_date=None,
                              end_date=None,
                              year=0,
                              number=0,
                              name='',
                              version=Version.LOTV)
    next_next_season.save()
    logger.info("created empty season %d" % next_next_season.id)

    # Fixing rankings if they ended up with data time after season end.

    rankings = Ranking.objects.filter(season=season,
                                      status__in=(Ranking.COMPLETE_WITH_DATA, Ranking.COMPLETE_WITOUT_DATA),
                                      data_time__gte=season.end_time()).order_by('-id')

    for i, ranking in enumerate(rankings):
        ranking.data_time = season.end_time() - timedelta(seconds=i)
        ranking.save()
        logger.info("changed data_time to %s for ranking %d since it was after season break" %
                    (ranking.data_time, ranking.id))

    # Warn about the event to make monitoring send eamil.
        
    logger.warning("season break detected, current is now season %d, start_date %s" %
                   (next_season.id, next_season.start_date))


def update_season_cache(api_season, region, api_response):
    # Update or create the season cache, just for bookkeeping.
    try:
        cache = Cache.objects.get(region=region, type=Cache.SEASON, bid=1)
        cache.updated = api_response.fetch_time
        cache.data = api_season.to_text()
        cache.save()
    except Cache.DoesNotExist:
        Cache.objects.create(url=api_season.url, bid=1, type=Cache.SEASON, region=region,
                             status=api_response.status, created=api_response.fetch_time,
                             updated=api_response.fetch_time, data=api_season.to_text())


@log_context(feature='new')
def fetch_new(region=None, check_stop=lambda: None, bnet_client=None):

    with transaction.atomic():

        current_season = Season.get_current_season()

        for count in range(1, 3):
            check_stop()

            res = bnet_client.fetch_current_season(region)
            api_season = res.api_season

            if res.status == 200:
                update_season_cache(api_season, region, res)

                # Check season.
                if current_season.id == api_season.season_id():
                    # We already have latest season, continue with fetch.
                    break
        
                elif current_season.id + 1 == api_season.season_id():
                    # New season detected, create new season and wait for next fetch new.
                    create_new_season(current_season, api_season.start_date())
                    return
                
                elif current_season.near_start(utcnow(), days=2):
                    logger.info("current season %d near start, blizzard says %d, probably cached or other region"
                                ", bailing" % (current_season.id, api_season.season_id()))
                    return
                
                else:
                    raise Exception("season mismatch blizzard says %d, current in db is %d" %
                                    (api_season.season_id(), current_season.id))

        else:
            # Is should be safe to continue after this since season id is in call to blizzard api. This is info logging
            # because it happens all the time due to some blizzard bug.
            logger.log(INFO, "could not get season info from %s after %d tries, status %s, skipping season check" %
                       (api_season.url, count, res.status))

    fetch_new_in_region(check_stop, bnet_client, current_season, region)


