from datetime import datetime, timezone

from logging import getLogger, INFO, WARNING

from django.db import transaction

from main.models import Cache, Ladder, Mode, League, Version, Region
from common.utils import to_unix
from lib import sc2


logger = getLogger('django')
sc2.set_logger(logger)


def update_ladder_cache(cpp, ranking, ladder, status, api_ladder, fetch_time):
    """
    Update cache and link/unlink. The fetch is done for a specific ranking and ladder, both provided. Since this is a
    refetch of a present GOOD ladder (or it is becoming GOOD) only 200 responses are allowed. Transaction should be
    spanning call to make transaction abortion possible.
    """

    try:
        lc = ranking.sources.get(region=ladder.region, bid=ladder.bid, type=Cache.LADDER)

    except Cache.DoesNotExist:
        lc = None

    lc = lc or Cache(region=ladder.region,
                     bid=ladder.bid,
                     type=Cache.LADDER,
                     created=fetch_time)
    lc.ranking = ranking
    lc.data = api_ladder.to_text()
    lc.url = api_ladder.url
    lc.updated = fetch_time
    lc.status = status
    lc.save()

    ladder.updated = fetch_time
    ladder.last_join = api_ladder.last_join()
    ladder.max_points = api_ladder.max_points()
    ladder.member_count = api_ladder.member_count()
    ladder.strangeness = Ladder.GOOD
    ladder.save()

    team_size = Mode.team_size(ladder.mode)
    return cpp.update_with_ladder(ladder.id,
                                  lc.id,
                                  ladder.region,
                                  ladder.mode,
                                  ladder.league,
                                  ladder.tier,
                                  ladder.version,
                                  ladder.season_id,
                                  to_unix(lc.updated),
                                  lc.updated.date().isoformat(),
                                  team_size,
                                  api_ladder.members_for_ranking(team_size))


S22_END_TIME = datetime(2015, 6, 29, 23, 59, 59, 999, timezone.utc)


def fetch_new_ladder(bnet_client, season, region, version, mode, league, tier, bid):
    """ Fetch a previously unknown ladder, save ladder and cache. """

    res = bnet_client.fetch_ladder(region, bid)
    al = res.api_ladder

    if res.status == 503:
        logger.error("got 503 from %s, exiting" % al.url)
        raise SystemExit()

    ladder = Ladder(region=region, bid=bid, created=res.fetch_time, updated=res.fetch_time)
    ladder.season = season
    ladder.version = version
    ladder.mode = mode
    ladder.league = league
    ladder.tier = tier
    ladder.strangeness = Ladder.MISSING

    try:
        # Sanity check, there should never be a cache already.
        cache = Cache.objects.get(region=region, bid=bid, type=Cache.LADDER)
        raise Exception("cache %d already exists for region %s, bid %s, did not expect this" % (cache.id, region, bid))
    except Cache.DoesNotExist:
        cache = Cache(region=region, bid=bid, type=Cache.LADDER, url=al.url, created=res.fetch_time, retry_count=0)

    cache.status = res.status
    cache.data = al.to_text()
    cache.updated = res.fetch_time

    if res.status == 200:
        ladder.strangeness = Ladder.GOOD
        ladder.max_points = al.max_points()
        ladder.first_join = al.first_join()
        ladder.last_join = al.last_join()
        ladder.member_count = al.member_count()

    ladder.save()

    cache.ladder = ladder
    cache.save()

    logger.info("saved new ladder %s (bid %d) as %s with cache %d" % (ladder.id, ladder.bid, ladder.info(), cache.id))


def fetch_new_in_league(check_stop, bnet_client, region, season, version, mode, league):
    """ Fetch league and make sure all ladders exists, fetch new ones if needed. """

    for count in range(1, 5):
        check_stop()

        res = bnet_client.fetch_league(region, season.id, version, mode, league)
        api_league = res.api_league

        if res.status == 503:
            logger.error("got 503 from %s, exiting" % api_league.url)
            raise SystemExit()

        if res.status == 404 and league == League.GRANDMASTER:
            return

        if res.status == 200:
            break

    else:
        level = INFO if region == Region.CN else WARNING
        logger.log(level, "fetched league %s after %d tries, status %s, skipping" % (api_league.url, count, res.status))
        return

    logger.info("fetched league %s, bid %s, season %s, %s, %s, %s, %s ladders" %
                (api_league.url, api_league.bid, season.id, Version.key_by_ids[version], Mode.key_by_ids[mode],
                 League.key_by_ids[league], api_league.count()))

    with transaction.atomic():

        # Update or create the league cache, just for bookkeeping.
        try:
            cache = Cache.objects.get(region=region, type=Cache.LEAGUE, bid=api_league.bid)
            cache.updated = res.fetch_time
            cache.data = api_league.to_text()
            cache.save()
        except Cache.DoesNotExist:
            Cache.objects.create(url=api_league.url, bid=api_league.bid, type=Cache.LEAGUE, region=region,
                                 status=res.status, created=res.fetch_time, updated=res.fetch_time,
                                 data=api_league.to_text())

        for tier in range(3):
            check_stop()
            for bid in api_league.tier_bids(tier):
                try:
                    ladder = Ladder.objects.get(region=region, bid=bid)

                    # Handle strange and wrong tier ladders from season 28 and 29, remove code after. Fixed for all
                    # but SEA, wait for a while longer before removing.
                    if ladder.strangeness in (Ladder.STRANGE, Ladder.NYD, Ladder.NOP) or ladder.tier != tier:
                        ladder.version = version
                        ladder.mode = mode
                        ladder.league = league
                        ladder.tier = tier
                        ladder.strangeness = Ladder.GOOD
                        ladder.save()
                        logger.info("reparied ladder %s (bid %d) as %s with cache %d" %
                                    (ladder.id, ladder.bid, ladder.info(), ladder.get_ladder_cache().id))

                except Ladder.DoesNotExist:
                    fetch_new_ladder(bnet_client, season, region, version, mode, league, tier, bid)


def fetch_new_in_region(check_stop=lambda: None, bnet_client=None, season=None, region=None):
    """ Fetch all leagues for season and region, fetch new ladders if needed. """

    for version in [Version.LOTV]:
        for mode in Mode.ranking_ids:
            for league in reversed(League.ranking_ids):
                if version != Version.LOTV and mode == Mode.ARCHON:
                    continue

                check_stop()
                fetch_new_in_league(check_stop, bnet_client, region, season, version, mode, league)


