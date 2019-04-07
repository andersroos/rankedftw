from django.urls import reverse
from django.views.generic.base import View
from django.http import HttpResponse
from django.utils.http import http_date, parse_http_date

from common.utils import to_unix, utcnow
from main.views.base import MainNavMixin, Nav, rankings_view_client, CachingTemplateView, get_season_list,\
    last_updated_info
from common.cache import cache_value, cache_control
from main.models import RankingStats, League, Region, Race, Mode, Version


def ranking_stats_last_modified():
    rs = RankingStats.objects.all().order_by('-updated')[:1][0]
    return rs.updated


class StatsSubNav(object):
    """ Adds the stats sub nav to a view. """

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['sub_nav'] = Nav(self.request, 'Stat', levels=0) \
            .add('Leagues',
                 reverse('stats-leagues', kwargs={'mode_key': self.mode_key}),
                 'League statistics over time.') \
            .add('Races',
                 reverse('stats-races', kwargs={'mode_key': self.mode_key}),
                 'Race statistics over time.') \
            .add('Population',
                 reverse('stats-population', kwargs={'mode_key': self.mode_key}),
                 'Player population statistics over time.')

        nav = Nav(self.request, 'Mode', levels=0)
        for mode_id in sorted(Mode.ranking_ids):
            nav.add(Mode.name_by_ids[mode_id],
                    reverse(self.request.resolver_match.view_name, kwargs={'mode_key': Mode.key_by_ids[mode_id]}))
        context['sub_sub_nav'] = nav
        
        return context


class StatsView(StatsSubNav, CachingTemplateView):
    """ Generic stats view. """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['last_updated'], _ = last_updated_info()
        context['versions'] = list(reversed(Version.ranking_ids))
        context['leagues'] = list(reversed(League.ranking_ids))
        context['races'] = [r for r in Race.ranking_ids if r != Race.UNKNOWN] + [Race.UNKNOWN]  # Make better order.
        context['regions'] = [Region.ALL] + Region.ranking_ids
        context['seasons'] = get_season_list()
        context['mode_id'] = self.mode_id
        context['mode_got_race_stats'] = Mode.team_size(self.mode_id) == 1 or self.mode_id == Mode.ARCHON
        return context

    @cache_control("max-age=3600")
    def get(self, request, mode_key=None):
        try:
            self.mode_key = mode_key
            self.mode_id = Mode.id_by_keys[mode_key]
        except KeyError:
            return HttpResponse(status=404)
        
        context = self.get_context_data()
        
        return self.render_to_response(context)

        
class StatsRaw(View):

    def get(self, request, mode_id=None):
        mode_id = int(mode_id)
        if not (mode_id in Mode.stat_v1_ids):
            return HttpResponse(status=404)
        
        last_updated = to_unix(cache_value("ranking_stats_last_modified", 600, ranking_stats_last_modified))
        now = to_unix(utcnow())
        
        try:
            if_modified_since = parse_http_date(request.META['HTTP_IF_MODIFIED_SINCE'])
        except (ValueError, KeyError):
            if_modified_since = 0
        
        if if_modified_since >= last_updated:
            response = HttpResponse("", content_type="application/json", status=304)
        else:
            response = HttpResponse(cache_value("ranking_stats_%d" % mode_id, 600,
                                                rankings_view_client, 'ranking_stats', mode_id),
                                    content_type="application/json")
            
        response['Cache-Control'] = "max-age=86400"
        response['Date'] = http_date(now)
        response['Expires'] = http_date(now + 86400)
        response['Last-Modified'] = http_date(last_updated)
        return response
