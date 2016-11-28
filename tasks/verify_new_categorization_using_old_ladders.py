#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import init_django

from tasks.base import Command, RegionsArgMixin
from json import loads
from main.battle_net import ApiLadder, ApiPlayerLadders
from main.categorizer import get_version_mode_league, get_season_based_on_join_times, determine_season, get_strangeness
from main.models import Season, Region, Ladder, Cache

#
# Categorization code was rewritten near the end of season 25 to make it handle automatic end of season detection.
#
# When validating all historic categorization with the new algorithm not all matched. Complete log:
# sc2-data/log/verify_new_categorization_using_old_ladders.log.
#


class Main(RegionsArgMixin, Command):

    def __init__(self):
        super().__init__("",
                         pid_file=False, stoppable=True)
        self.add_argument('--start-season', '-ss', dest="ss_id", type=int, default=1,
                          help="The start season id.")
        self.add_argument('--end-season', '-es', dest="es_id", type=int, default=26,
                          help="The end season id.")
        self.add_argument('--ff', '-f', dest="bid", type=int, default=0,
                          help="Fast forward to ladder with bid.")
        self.add_argument('--verify', '-v', dest="verify", type=str,
                          default="season_id,strangeness,league,version,mode")

    def run(self, args, logger):
        seasons = list(Season.objects.filter(pk__gte=args.ss_id, pk__lte=args.es_id))

        for region in args.regions:
            logger.info("processing region %s" % region)

            for ladder in Ladder.objects.filter(season__in=seasons, region=region, bid__gte=args.bid).order_by('bid'):

                self.check_stop()

                context = "ladder %d, region %s, bid %d, %s" %\
                          (ladder.id, Region.key_by_ids[region], ladder.bid, ladder.info())

                try:
                    lcs = ladder.cached_raw.filter(type=Cache.LADDER).order_by('id')
                    if len(lcs) != 1:
                        raise Exception("expected one ladder cache for ladder %d, found %s" %
                                        (ladder.id, [c.id for c in lcs]))
                    lc = lcs[0]
                    if lc.bid != ladder.bid or lc.region != ladder.region:
                        raise Exception("bid or region did not match lc on %s" % ladder.id)

                    al = ApiLadder(loads(lc.data), lc.url)

                    pcs = ladder.cached_raw.filter(type=Cache.PLAYER_LADDERS)
                    if len(pcs) > 1:
                        raise Exception("expected one player ladders cache for ladder %d, found %s" %
                                        (ladder.id, [c.id for c in pcs]))
                    pc = pcs[0] if pcs else None
                    if pc:
                        if pc.region != ladder.region:
                            raise Exception("region did not match pc on %s, %s" % ladder.id)
                        ap = ApiPlayerLadders(loads(pc.data), pc.url)
                    else:
                        ap = None

                    new = Ladder()

                    join_season, join_valid = get_season_based_on_join_times(al.first_join(), al.last_join())
                    if ap:
                        match = ap.refers(ladder.bid)
                        if not match:
                            logger.error("%s: failed match" % context)
                            continue

                        context += ", match %s" % match

                        new.season, valid = determine_season(fetch_time=lc.updated, match=match,
                                                             join_season=join_season, join_valid=join_valid)
                    else:
                        new.season, valid = join_season, join_valid
                        context += ", match None"

                    new.version, new.mode, new.league = get_version_mode_league(ladder.bid, new.season, al, ap)

                    new.strangeness = get_strangeness(lc.updated, al, ap)

                    for what in args.verify.split(','):
                        nv = getattr(new, what)
                        ov = getattr(ladder, what)
                        if nv != ov:
                            if new.strangeness in (Ladder.GOOD, Ladder.NOP):
                                log = logger.error
                            else:
                                log = logger.warning
                            log("%s: failed %s, old %s, new %s" % (context, what, ov, nv))
                            break
                    else:
                        logger.info("%s: success" % context)

                except Exception as e:
                    logger.error("%s: %s(\"%s\")" % (context, e.__class__.__name__, e))

        return 0


if __name__ == '__main__':
    Main()()

