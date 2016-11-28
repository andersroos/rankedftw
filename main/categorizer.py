from datetime import timedelta, datetime, timezone
from logging import getLogger
from main.models import Season, Ladder, Mode, Version, League

logger = getLogger('django')

# This code is used to categorize ladders before season 28 when blizzard added the league api. It is kept to be able
# to possibly fix errors in pre season 28 categorization but it is not in active use.

# NOTE Categorization code was rewritten near the end of season 25 to make it handle automatic end of season
# detection, see verify_new_categorization_using_old_ladders.py for details.


class CatError(Exception):
    """ This is for really bad errors that can happen, Exceptions has never happened so far. """
    pass


def get_season_based_on_join_times(first_join, last_join):
    """
    Get season based off first and last join times only.

    Return <season, value>, valid will be 0 if sure, -1 if could be season before +1 if could be season after (if
    both joins are to close to boundary).

    Season boundaries will not be exact (also join time is in unknown time zone), since we switch autimatically they
    will be on the date after switch or event two days after because of different time zones. Also ladders have been
    created well before season start some time.

    If both times are near a boundary the last_join will be used against the stored value on the season (this will make
    it more likely to fall in the first season). If there is player ladder data it will sort this out, if there is not
    it may stay wrong.

    NOTE: Join times can be off by serveral days, like 3-4 days. If both joins are too close to the same season end
    valid will be -1 or +1 and join season could be off by one season.

    """

    context = "first_join %s, last_join %s" % (first_join, last_join)

    if last_join < first_join:
        raise Exception("%s, last_join is before first_join, this is strange" % context)

    first_season = Season.get_active(first_join)
    last_season = Season.get_active(last_join)

    context += ", first_season %s, last_season %d" % (first_season.id, last_season.id)

    if first_season.id == last_season.id:
        # Same season matched, this should be the most common case.

        if first_season.is_open() and not (first_season.near_start(first_join) or last_season.near_start(last_join))\
                or not first_season.is_open() and first_season.near_end(first_join):
            # Compact join period to the end of season, insecure, could be season after.
            return last_season, 1

        if last_season.near_start(last_join):
            # Compact join period to the start of season, insecure, could be season before.
            return last_season, -1

        # One/both join in the middle or first in beginning and last in end, secure.
        return last_season, 0

    if first_season.id + 1 == last_season.id:
        # End points in different seasons, prefer determine by last_join, but it depends on how valid it is.
        if last_season.near_start(last_join):
            # Last end is unsure.
            if first_season.near_end(first_join):
                # First end is also unsure, pick last_season, but may be season before.
                return last_season, -1

            # First end is sure, pick first season.
            return first_season, 0

        if first_season.near_end(first_join):
            # First end is unsure, pick last season.
            return last_season, 0

        # This means both are sure but in different seasons.
        raise CatError("%s, can't determine season this ladder seems to span full seasons" % context)

    if first_season.id + 2 == last_season.id \
       and first_season.near_end(first_join) \
       and last_season.near_start(last_join):
        # Both ends are insecure, so it has to be season in the middle.
        return first_season.get_next(), 0

    raise CatError("%s, this must be buggy, seasons wrong order or too far apart" % context)


def get_season_based_on_fetch_time_and_match(fetch_time, match):
    """
    Mach is a really special snowflake, it can return curr when it is prev right after season switch but never prev
    instead of curr (since if a new ladder is referred the player_ladder is up to date). This code will trust that
    prev/curr is correct and let code outside make a sanity check and keep it as nyd if this fails.

    Returns the ladder's season based on fetch_time and match.
    """

    if match not in ('curr', 'prev'):
        raise Exception("match '%s' unexpected" % match)

    fetch_season = Season.get_active(fetch_time)

    if fetch_season.near_start(fetch_time):
        # May be season before if another region caused the season switch.
        fetch_valid = -1

    elif fetch_season.is_open() or fetch_season.near_end(fetch_time):
        # We may actually be in the next season.
        fetch_valid = 1
    else:

        # We are mid season so it is correct.
        fetch_valid = 0

    if match == 'prev':
        fetch_season = fetch_season.get_prev()

    return fetch_season, fetch_valid


def determine_season(fetch_time=None, match=None, fetch_season=None, fetch_valid=None,
                     first_join=None, last_join=None, join_season=None, join_valid=None):
    if fetch_season is None and fetch_valid is None:
        fetch_season, fetch_valid = get_season_based_on_fetch_time_and_match(fetch_time, match)

    if join_season is None and join_valid is None:
        join_season, join_valid = get_season_based_on_join_times(first_join, last_join)

    # Check if fetch_season, fetch_valid, join_season and join_valid can agree on anything.
    if not (fetch_season.id == join_season.id
            or fetch_season.id == join_season.id + join_valid
            or fetch_season.id + fetch_valid == join_season.id
            or fetch_season.id + fetch_valid == join_season.id + join_valid):
        raise Exception("%s match but fetch_season %d, fetch_valid %d, join_season %d, join_valid %d,"
                        " can't agree on season" % (match, fetch_season.id, fetch_valid, join_season.id, join_valid))

    if fetch_valid == 0 or join_valid == 0:
        # One is sure, so let's pick that.
        if fetch_valid == 0:
            return fetch_season, 0
        else:
            return join_season, 0

    if fetch_season.id == join_season.id and fetch_valid == join_valid:
        # Equal but unsure in same way, just return that.
        return fetch_season, fetch_valid

    if fetch_season.id == join_season.id:
        # Same but unsure in different ways -> sure.
        return fetch_season, 0

    # This means both are unsure but picked different seasons.

    if fetch_season.id + fetch_valid == join_season.id + join_valid:
        # There is only one common ground in the middle between them, so we are sure about that.
        return fetch_season.get_relative(fetch_valid), 0

    if fetch_season.id + fetch_valid == join_season.id and fetch_season.id == join_season.id + join_valid:
        # Not conclusive, choose based off fetch_season.
        return fetch_season, fetch_valid

    if fetch_season.id + fetch_valid == join_season.id:
        # Valids are equal so one common ground.
        return join_season, 0

    # One common ground but the other way.
    return fetch_season, 0


NEVER_AP_TIME = datetime(2013, 8, 27, 0, 0, 0, 0, timezone.utc)


def get_strangeness(fetch_time, al, ap):
    """ Return the strangeness of this ladder. """

    uncertain_age = \
        (fetch_time - al.first_join()) < timedelta(days=Season.LADDER_AGE_BEFORE_CATEGORIZING_UNCERTAIN_LADDER)

    # Check for certain sign of strange ladder (fraction in points are always strange ladders).

    count, bad_count, max_points = al.point_stats()

    if bad_count:
        if ap:
            raise Exception("matched player_ladder but strange, this should never happen")
        return Ladder.STRANGE

    # If we have matching ap so it is always good, or it is too old to have ap.

    if ap or al.last_join() < NEVER_AP_TIME:
        return Ladder.GOOD

    # If no ap but uncertain age, let's wait a bit.

    if uncertain_age:
        return Ladder.NYD

    # This is a strange case, let's nop. This can be caused by Blizzard API derping, bad luck of 500 streak for
    # small ladders or that everybody got promoted/left ladder.
    return Ladder.NOP


def get_version_mode_league(bid, season, al, ap=None):
    """ Return <version, mode, league>, they cam be unkown. """

    if ap:
        match = ap.refers(bid)
        return ap.get_version_mode_league(bid, match)

    version = Version.UNKNOWN
    if season and season.version == Version.WOL:
        version = Version.WOL

    mode = Mode.UNKNOWN
    team_size = al.team_size()
    if team_size == 2:
        mode = Mode.TEAM_2V2
    elif team_size == 3:
        mode = Mode.TEAM_3V3
    elif team_size == 4:
        mode = Mode.TEAM_4V4

    league = League.UNKNOWN
    return version, mode, league
