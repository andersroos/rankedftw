import json
import socket
from collections import deque
from datetime import timedelta
from logging import getLogger, INFO, WARNING
from time import sleep
from django.db import transaction
from common.utils import utcnow, to_unix, StoppableThread
from main.battle_net import BnetClient, ApiLadder
from main.client import request_udp, request_tcp
from main.fetch import update_ladder_cache
from main.models import Enums, Ladder, League, Mode, Version, Season, Ranking, get_db_name, Region
from common.logging import log_context, LogContext
from lib import sc2


logger = getLogger('django')
sc2.set_logger(logger)


def interleave(*queues):
    while any(queues):
        for q in queues:
            try:
                batch = q[-1]
                try:
                    yield batch.pop()
                except IndexError:
                    q.pop()
            except IndexError:
                pass


class FetcherThread(StoppableThread):

    DELAY_MAX = 256

    def __init__(self, season, region, fetched_queue, bnet_client):
        super(FetcherThread, self).__init__()
        self.bnet_client = bnet_client
        self.season = season
        self.region = region
        self.fetched_queue = fetched_queue
        self.gm_batches = deque()
        self.plat_batches = deque()
        self.rest_batches = deque()

    @log_context(feature='queue')
    def add(self, queue, what, batch):
        queues_len = sum((len(q) for q in queue))
        if len(queue) > 1:
            logger.info("%s queue has batch backlog (%d ladders), not adding" % (what, queues_len))
        else:
            logger.info("%s queue got new batch of length %d, length before was %d" % (what, len(batch), queues_len))
            queue.appendleft(batch)

    def add_gm(self, batch):
        self.add(self.gm_batches, 'gm', batch)

    def add_plat(self, batch):
        self.add(self.plat_batches, 'plat', batch)

    def add_rest(self, batch):
        self.add(self.rest_batches, 'rest', batch)

    def __iter__(self):
        return interleave(self.gm_batches, self.plat_batches, self.rest_batches)

    @log_context(feature='fetch')
    def do_run(self):

        delay = 1
        while not self.check_stop(throw=False):
            for ladder in self:
                self.check_stop()

                status, api_ladder, fetch_time, fetch_duration = \
                    self.bnet_client.fetch_ladder(self.season.id, ladder.region, ladder.bid, timeout=60)

                logger.info("fetched %s got %d in %.2fs, ladder %d, %s, %s, %s" %
                            (api_ladder.url, status, fetch_duration, ladder.bid, Mode.key_by_ids[ladder.mode],
                             Version.key_by_ids[ladder.version], League.key_by_ids[ladder.league]))

                if status == 200:
                    self.fetched_queue.appendleft((ladder, status, api_ladder, fetch_time))

                # Simple fetch throttle, 10 requests/s allowed -> 2/s/thread -> 0,5s min time.
                if fetch_duration < 0.5:
                    sleep(0.5 - fetch_duration + 0.1)
                elif fetch_duration < 1:
                    sleep(0.2)

                if status != 200 or len(self.fetched_queue) > 20:
                    delay = min(self.DELAY_MAX + 1, delay * 2)
                    if delay == self.DELAY_MAX:

                        level = INFO if self.region == Region.CN else WARNING
                        logger.log(level, "delay hit %ds, got many bad statuses (status now %d) or queue is too big "
                                          "(now %d)" % (self.DELAY_MAX, status, len(self.fetched_queue)))
                    for i in range(min(self.DELAY_MAX, delay)):
                        self.check_stop()
                        sleep(1)
                else:
                    delay = 1

            sleep(0.04)


class FetchManager(object):

    def __init__(self, ranking, regions, bnet_client):
        self.fetched_queue = deque()
        self.ranking = ranking
        self.regions = regions
        self.threads = {}
        for region in self.regions:
            thread = FetcherThread(ranking.season, region, self.fetched_queue, bnet_client)
            thread.start()
            self.threads[region] = thread

    def start_gm(self):
        for region, thread in sorted(self.threads.items()):
            ladders = deque(Ladder.objects
                            .filter(region=region,
                                    strangeness=Ladder.GOOD,
                                    season=self.ranking.season,
                                    league=League.GRANDMASTER)
                            .order_by('updated')
                            .all())
            thread.add_gm(ladders)

    def start_plat(self):
        for region, thread in sorted(self.threads.items()):
            ladders = deque(Ladder.objects
                            .filter(region=region,
                                    strangeness=Ladder.GOOD,
                                    season=self.ranking.season,
                                    league__gte=League.PLATINUM,
                                    mode=Mode.TEAM_1V1)
                            .exclude(league=League.GRANDMASTER)
                            .order_by('updated')
                            .all())
            thread.add_plat(ladders)

    def start_rest(self):
        for region, thread in sorted(self.threads.items()):
            ladders = deque(Ladder.objects
                            .filter(region=region,
                                    strangeness=Ladder.GOOD,
                                    season=self.ranking.season)
                            .exclude(mode=Mode.TEAM_1V1, league__gte=League.PLATINUM)
                            .exclude(league=League.GRANDMASTER)
                            .order_by('updated')
                            .all())
            thread.add_rest(ladders)

    def pop(self):
        return self.fetched_queue.pop()

    def stop(self):
        for thread in self.threads.values():
            thread.stop()

    def join(self):
        for thread in self.threads.values():
            thread.join()


class UpdateManager(object):
    """
    Handle how updates are managed. Holds the fetch manager and decides when ranking should be saved and when we
    pause to check for new ranking or new season.
    """

    server_ping_timeout = 10.0
    
    @classmethod
    def save_ranking(self, cpp, ranking, queue_length):
        ranking.set_data_time(ranking.season.reload(), cpp)

        logger.info("saving ranking %d, %d updates left in queue not included, new data_time is %s" %
                    (ranking.id, queue_length, ranking.data_time))
        cpp.save_data(ranking.id, ranking.season_id, to_unix(utcnow()))
        cpp.save_stats(ranking.id, to_unix(utcnow()))

        ranking.status = Ranking.COMPLETE_WITH_DATA
        ranking.save()

        # Ping server to reload ranking.
        try:
            raw = request_tcp('localhost', 4747,
                              json.dumps({'cmd': 'refresh'}).encode('utf-8'),
                              timeout=self.server_ping_timeout)
            response = json.loads(raw.decode('utf-8'))
            code = response.get('code')
            if code == 'ok':
                logger.info("refresh ping returned ok")
            else:
                logger.warning("refresh ping returned %s" % code)

        except OSError as e:
            logger.warning("refresh ping to server failed: " + str(e))

    @classmethod
    def update_until(self, ranking=None, cpp=None, regions=None, until=None, check_stop=None,
                     fetch_manager=None, bnet_client=None):
        """ Update until time until (utc) has passed and code outisde will decide if season and/or ranking switching
        should be done. """

        bnet_client = bnet_client or BnetClient()
        fetch_manager = fetch_manager or FetchManager(ranking, regions, bnet_client)

        try:

            logger.info("updating season %d, ranking %d, regions %s, until %s" %
                        (ranking.season_id, ranking.id, regions, until))

            last_save = utcnow()
            last_season_check = utcnow()
            last_gm = utcnow(days=-20)
            last_plat = utcnow(days=-20)
            last_rest = utcnow(days=-20)

            while not check_stop(throw=False):

                now = utcnow()

                if now > until:
                    logger.info("we reached until time %s, pausing to switch season/ranking" % until)
                    break

                if now - last_season_check > timedelta(minutes=30):
                    last_season_check = now
                    if ranking.season_id != Season.get_current_season().id:
                        logger.info("current season %d is closed, pausing to give chance for season switch" %
                                    ranking.season_id)
                        break

                if now - last_save > timedelta(seconds=60):
                    self.save_ranking(cpp, ranking, len(fetch_manager.fetched_queue))
                    last_save = utcnow()  # This can take a long time, so get new now again.

                if now - last_gm > timedelta(seconds=60):
                    last_gm = now
                    fetch_manager.start_gm()

                if now - last_plat > timedelta(minutes=10):
                    last_plat = now
                    fetch_manager.start_plat()

                if now - last_rest > timedelta(minutes=60):
                    last_rest = now
                    fetch_manager.start_rest()

                try:
                    ladder, status, api_ladder, fetch_time = fetch_manager.pop()

                    with transaction.atomic():
                        stats = update_ladder_cache(cpp, ranking, ladder, status, api_ladder, fetch_time)
                        with LogContext(region=ladder.region):
                            logger.info("saved updated ladder %d and added data to ranking %d, "
                                        "updated %d players %d teams, inserted %d players %d teams, "
                                        "cache sizes %d players %d teams" %
                                        (ladder.id,
                                         ranking.id,
                                         stats["updated_player_count"],
                                         stats["updated_team_count"],
                                         stats["inserted_player_count"],
                                         stats["inserted_team_count"],
                                         stats["player_cache_size"],
                                         stats["team_cache_size"],
                                         ))

                except IndexError:
                    sleep(0.04)

            logger.info("stopped fetching, saving")
            fetch_manager.stop()
            fetch_manager.join()
            self.save_ranking(cpp, ranking, len(fetch_manager.fetched_queue))
        except Exception:
            fetch_manager.stop()
            raise
        cpp.release()


@log_context(region='ALL', feature='update')
def countinously_update(regions=None, check_stop=None, update_manager=None, switch_hour=10):

    update_manager = update_manager or UpdateManager()

    ranking = Ranking.objects.order_by('-id').first()

    if ranking.status != Ranking.COMPLETE_WITH_DATA:
        raise Exception("ranking %d is not in a good state, clean up" % ranking.id)

    season = ranking.season

    cpp = sc2.RankingData(get_db_name(), Enums.INFO)

    while not check_stop(throw=False):

        # Check if we want to switch to new season.

        current_season = Season.get_current_season()
        if current_season.id != season.id:

            if current_season.id != season.get_next().id:
                raise Exception("something is really wrong, current season is not next")

            if Ladder.objects.filter(season=current_season, strangeness=Ladder.GOOD).count() > 8:
                season = current_season
                logger.info("switching to rank new season %d multiple new season ladders was detected" % season.id)

        # Do we want to create new ranking? We want to switch around switch_hour UTC every day but not if ranking is
        # too young. If too old, switch anyway.
        now = utcnow()

        if season.id != ranking.season_id:
            # Create new ranking based on new season.
            ranking = Ranking.objects.create(season=season,
                                             created=now,
                                             data_time=season.start_time(),
                                             min_data_time=season.start_time(),
                                             max_data_time=season.start_time(),
                                             status=Ranking.CREATED)
            logger.info("created new ranking %d based on new season %d" % (ranking.id, season.id))

            cpp.clear_team_ranks()
            cpp.reconnect_db()
            update_manager.save_ranking(cpp, ranking, 0)

        elif ((ranking.created + timedelta(hours=48) < now
               or (ranking.created + timedelta(hours=12) < now and now.hour == switch_hour))
              and not ranking.season.near_start(now, days=4)):
            # Create a new ranking within the season.

            cpp.clear_team_ranks()
            cpp.reconnect_db()

            with transaction.atomic():
                new_ranking = Ranking.objects.create(season=season,
                                                     created=now,
                                                     data_time=ranking.data_time,
                                                     min_data_time=ranking.min_data_time,
                                                     max_data_time=ranking.max_data_time,
                                                     status=Ranking.CREATED)
                # Copy all caches of old ranking to new ranking. Also remake the full ranking while doing so to get
                # rid of leave leaguers.

                logger.info("created new ranking %d basing it on copy of ranking %d, seaons %d" %
                            (new_ranking.id, ranking.id, season.id))

                count = ranking.sources.count()
                logger.info("copying %d cached ladders from ranking %d to ranking %d and adding them to ranking" %
                            (count, ranking.id, new_ranking.id))

                for i, lc in enumerate(ranking.sources.all(), start=1):
                    lc.pk = None
                    lc.created = utcnow()
                    lc.ladder = None
                    lc.ranking = ranking
                    lc.save()

                    new_ranking.sources.add(lc)

                    ladder = Ladder.objects.get(region=lc.region, bid=lc.bid)
                    team_size = Mode.team_size(ladder.mode)
                    stats = cpp.update_with_ladder(ladder.id,
                                                   lc.id,
                                                   ladder.region,
                                                   ladder.mode,
                                                   ladder.league,
                                                   ladder.tier,
                                                   ladder.version,
                                                   ladder.season_id,
                                                   to_unix(lc.updated),
                                                   team_size,
                                                   ApiLadder(lc.data, lc.url).members_for_ranking(team_size))

                    if i % 100 == 0:
                        logger.info("copied and added cache %d/%d, player cache size %d, team cache size %d" %
                                    (i, count, stats['player_cache_size'], stats['team_cache_size']))

            ranking = new_ranking
            update_manager.save_ranking(cpp, ranking, 0)
        else:
            logger.info("continuing with ranking %d, season %d" % (ranking.id, season.id))
            cpp.reconnect_db()
            cpp.load(ranking.id)

        now = utcnow()
        until = now.replace(hour=switch_hour, minute=0, second=0)
        if until < now:
            until += timedelta(hours=24)

        update_manager.update_until(ranking=ranking, cpp=cpp, regions=regions,
                                    until=until, check_stop=check_stop)
