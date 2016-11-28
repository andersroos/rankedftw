import math
from logging import getLogger

from django.views.generic.base import TemplateView

from common.utils import to_unix, utcnow
from main.models import Team, Region, League, Race, Version, Mode
from main.client import ClientError, client
from common.cache import cache_value, cache_control
from main.views.base import MainNavMixin, Nav
from django.http import Http404
from django.core import urlresolvers
from copy import copy


logger = getLogger('django')


PAGE_SIZE = 100


# MMR is 5 in c++ and league-points is 0, quick fix for now.
sort_keys = {"ladder-rank": 5,
             "played": 1,
             "wins": 2,
             "losses": 3,
             "win-rate": 4}


#
# About offset and team_id, it is pretty complicated.
#
# Representation:
#   team_id > 0 is valid, unset is 0
#   offset >= 0 is valid, unset is None in python and -1 in c++ (after parse)
#
# Request:
#   team_id, default is 0 (used if invalid or not set)
#   offset, default is None (used if invalid or not set)
#
# Server:
#   if offset is set, offset is used
#   if offset is unset and team_id is set, team_id is used for getting
#   if offset unset and team_id is unset -> first page
#
# Generated url:
#   unset values will not generate url parameters
#   if team_id is set it is kept on all navigation (to be able to see team in different sorting/filtering)
#   offset is set for page navigation, even to 0 (to be able to go to first page even if team_id is set)
#   offset is never set for sorting/filtering links (or team_id setting does not kick in)
#   if team_id is unset and offset = 0 (or <0) url will be generated without offet to help with caching
#

class FetchFail(Exception):
    pass


def ladder_url(request, paths=None, args=None, name=None, key=None):

    if name in paths:
        paths = copy(paths)
        paths[name] = key

    args = copy(args)
    if name in args or name == 'offset':
        args[name] = key

    url = urlresolvers.reverse('ladder', kwargs=paths)

    team_id = args.pop('team_id', None)
    offset = args.pop('offset', None)

    separator = '?'

    filters = [v for k, v in args.items() if v is not None and v != Region.ALL_KEY]
    if filters:
        url += '%sf=%s' % (separator, ','.join(filters))
        separator = '&'

    if team_id:
        url += '%steam=%d' % (separator, team_id)
        separator = '&'

    if offset is not None and (offset > 0 or team_id):
        url += '%soffset=%d' % (separator, max(0, offset))

    return url


class LadderCommon(object):

    @staticmethod
    def set_nav(context, request, url_func, paths, args, name=None, values=None, highlight=647965):
        """
        Build nav and set it in context for dimension name, url_func is used to build the url. All current request paths
        are in path argument, current url arguments are in args. Values is sequence of <option name, option key>. If a
        different key than the current one in paths or args should be highlighted set that key in highlight.
        Dimension name is also used for key in context.

        """

        value = paths.get(name)
        if not value:
            value = args.get(name)

        if highlight == 647965:
            highlight = value

        context['%s_nav' % name] = [('visiting' if highlight == key else '',
                                     title,
                                     key,
                                     url_func(request, paths, args, name, key))
                                    for title, key in values]

    @staticmethod
    def update_age(data):
        """ Update age of ladder data to present it as correctly as possible (to not be cached in outer layers). """
        now = to_unix(utcnow())
        for t in data['teams']:
            delta = now - int(t["data_time"])
            if delta < 3600:
                t["age"] = "%dm" % max((delta + 60) // 60, 1)
            else:
                t["age"] = "%dh" % (delta // 3600)

    @staticmethod
    def extract_filters(request):
        # Filters
        region_id = race_id = league_id = None
        for tag in request.GET.get('f', '').split(','):
            try:
                region_id = Region.id_by_keys[tag]
                region_id = region_id if region_id >= 0 else None
                continue
            except:
                pass

            try:
                race_id = Race.id_by_keys[tag]
                continue
            except:
                pass

            try:
                league_id = League.id_by_keys[tag]
                league_id = league_id if league_id >= 0 else None
                continue
            except:
                pass

        return region_id, race_id, league_id

    @staticmethod
    def extract_common(reverse=None, sort_key=None):

        # Reverse
        is_reverse = '-' == reverse

        # Sort Key
        try:
            sort_key_id = sort_keys[sort_key]
        except:
            raise Http404("Non existent sort key.")

        return is_reverse, sort_key_id

    @staticmethod
    def extract_rest(request, version=None, mode=None):
        # Version
        try:
            version_id = Version.id_by_keys[version]
            if version_id == Version.UNKNOWN:
                raise Exception()
        except:
            raise Http404("Non existent version.")

        # Mode
        try:
            mode_id = Mode.id_by_keys[mode]
            if mode_id == Mode.UNKNOWN:
                raise Exception()
        except:
            raise Http404("Non existent mode.")

        # Team
        try:
            team_id = int(request.GET.get('team', 0))
        except:
            team_id = 0
        if not (0 <= team_id < 2e9):
            raise Http404("Team id out of range.")

        # Offset
        try:
            request_offset = max(int(request.GET.get('offset')), 0)
        except:
            request_offset = None
        if request_offset and request_offset >= 2e9:
            raise Http404("Offset out of range.")

        return version_id, mode_id, team_id, request_offset


class LadderView(MainNavMixin, TemplateView, LadderCommon):

    @staticmethod
    def fetch_data(sort_key_id, version_id, mode_id, is_reverse=False, league_id=None,
                   region_id=None, race_id=None, offset=None, team_id=0,
                   limit=PAGE_SIZE):

        # Fetch data from server.

        data = client.get_ladder(sort_key_id, version_id, mode_id, reverse=is_reverse, league=league_id,
                                 region=region_id, race=race_id, offset=offset, team_id=team_id,
                                 limit=PAGE_SIZE)

        # Fetch information about teams from database.

        teams = data['teams']

        team_ids = {team["team_id"] for team in teams}
        team_mapping = {team.id: team
                        for team in
                        Team.objects
                        .filter(id__in=team_ids)
                        .all()
                        .select_related('member0', 'member1', 'member2', 'member3')}

        for tr in teams:
            t = team_mapping[tr["team_id"]]

            tr['rank'] += 1

            tr["m0_id"] = t.member0.id
            tr["m0_name"] = t.member0.name
            tr["m0_tag"] = t.member0.tag

            if t.member1:
                tr["m1_id"] = t.member1.id
                tr["m1_name"] = t.member1.name
                tr["m1_tag"] = t.member1.tag

            if t.member2:
                tr["m2_id"] = t.member2.id
                tr["m2_name"] = t.member2.name
                tr["m2_tag"] = t.member2.tag

            if t.member3:
                tr["m3_id"] = t.member3.id
                tr["m3_name"] = t.member3.name
                tr["m3_tag"] = t.member3.tag

        return data

    @cache_control("max-age=40")
    def get(self, request, version=None, mode=None, reverse=None, sort_key=None):

        context = self.get_context_data()

        #
        # Parse parameters.
        #

        region_id, race_id, league_id = self.extract_filters(request)
        is_reverse, sort_key_id = self.extract_common(reverse, sort_key)
        version_id, mode_id, team_id, request_offset = self.extract_rest(request, version, mode)

        #
        # Fetch data.
        #

        team_size = Mode.team_size(mode_id)
        filter_race = None if mode_id != Mode.ARCHON and team_size > 1 else race_id
        try:
            if (request_offset is None or request_offset == 0) and not team_id:
                key = "%s-%s-%s-%s-%s-%s-%s" % (sort_key_id, version_id, mode_id, is_reverse,
                                                league_id, region_id, filter_race)

                data = cache_value(key, 40, self.fetch_data, sort_key_id, version_id, mode_id,
                                   is_reverse=is_reverse, league_id=league_id, region_id=region_id,
                                   race_id=filter_race, limit=PAGE_SIZE)
            else:
                data = self.fetch_data(sort_key_id, version_id, mode_id,
                                       is_reverse=is_reverse, league_id=league_id, region_id=region_id,
                                       race_id=filter_race, offset=request_offset, team_id=team_id, limit=PAGE_SIZE)

        except ClientError as e:
            logger.error("Fetch from client error: %s" % str(e))
            context['error'] = 'The server is not feeling well, try again later.'
            return self.render_to_response(context)

        LadderCommon.update_age(data)

        context['ladder'] = data
        context['highlight_team_id'] = team_id
        context['team_size'] = team_size
        context['mode_id'] = mode_id

        #
        # Build navigation based on current parameters.
        #

        paths = {
            'version': version,
            'mode': mode,
            'reverse': reverse,
            'sort_key': sort_key,
        }

        args = {
            'region': Region.key_by_ids.get(region_id, Region.ALL_KEY),
            'league': League.key_by_ids.get(league_id),
            'race': Race.key_by_ids.get(race_id),
            'team_id': team_id,
        }

        values = [(Mode.name_by_ids[i], Mode.key_by_ids[i])
                  for i in sorted(Mode.ids) if i != Mode.UNKNOWN]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='mode', values=values)

        values = [(Version.name_by_ids[i], Version.key_by_ids[i])
                  for i in reversed(Version.ids) if i != Version.UNKNOWN]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='version', values=values)

        context['reverse_visiting'] = 'visiting' if reverse else ''
        context['reverse_href'] = ladder_url(request, paths, args, 'reverse', '' if reverse else '-')

        values = [('Ladder rank', 'ladder-rank'), ('Games played', 'played'), ('Wins', 'wins'),
                  ('Losses', 'losses'), ('Win rate', 'win-rate')]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='sort_key', values=values)

        values = [('All', None)] + [(Race.name_by_ids[i], Race.key_by_ids[i])
                                    for i in Race.ids if i != Race.UNKNOWN]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='race', values=values, highlight=Race.key_by_ids.get(filter_race))

        values = [('All', None)] + [(League.name_by_ids[i], League.key_by_ids[i])
                                    for i in League.ids if i != League.UNKNOWN]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='league', values=values)

        values = [(Region.name_by_ids[i], Region.key_by_ids[i])
                  for i in Region.ids if i != Region.UNKNOWN]
        LadderCommon.set_nav(context, request, ladder_url, paths, args,
                             name='region', values=values)

        #
        # Buld pagination, page is 0 indexed (+1 when displayed).
        #
        
        pages = []
        count = data['count']
        data_offset = data['offset']

        # page size: 4
        # ladder:  0  1  2  3| 4  5  6  7| 8  9 10 11|12 13
        # offset:                             ^             => current_page = 3, page_offset = 3
        # pages:   0| 1  2  3  4| 5  6  7  8| 9 10 11 12|13

        if data_offset >= count:
            current_page = -1
        else:
            current_page = math.ceil(data_offset / PAGE_SIZE)
            
        page_offset = -data_offset % PAGE_SIZE
        page_count = math.ceil((count + page_offset) / PAGE_SIZE)
        
        BEG_SIZE = 4
        MID_SIZE = 7  # Should be uneven.
        END_SIZE = 4

        start = 0
        end = min(BEG_SIZE, page_count)

        i = 0
        for i in range(start, end):
            page_index = PAGE_SIZE * i - page_offset
            pages.append({'index': i, 'href': ladder_url(request, paths, args, name='offset', key=page_index)})

        start = min(max(i + 1, current_page - MID_SIZE // 2), page_count)
        end = min(current_page + 1 + MID_SIZE // 2, page_count)
            
        if start > i + 1: pages.append({'gap': True})

        for i in range(start, end):
            page_index = PAGE_SIZE * i - page_offset
            pages.append({'index': i, 'href': ladder_url(request, paths, args, name='offset', key=page_index)})

        start = max(i + 1, page_count - END_SIZE)
        end = page_count

        if start > i + 1: pages.append({'gap': True})

        for i in range(start, end):
            page_index = PAGE_SIZE * i - page_offset
            pages.append({'index': i, 'href': ladder_url(request, paths, args, name='offset', key=page_index)})
            
        context['pages'] = pages if len(pages) > 1 else None
        context['current_page'] = current_page
        context['page_offset'] = page_offset
        context['page_count'] = page_count

        return self.render_to_response(context)

