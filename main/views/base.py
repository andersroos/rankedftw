from datetime import date
import json

from django.conf import settings
import gc
from lib import sc2
from common.cache import cache_control, cache_value
from common.utils import to_unix, utcnow
from django.db.models import Max
from main.models import Season, Ranking, Cache, Mode, Version, Enums
from django.views.generic.base import TemplateView, RedirectView
from django.core.urlresolvers import reverse


DEFAULT_SORT_KEY = 'mmr'
SORT_KEYS = {
    "league-points": 0,
    "played": 1,
    "wins": 2,
    "losses": 3,
    "win-rate": 4,
    "mmr": 5,
}


SEASON_FILTER = 14


def _get_season_list():
    return json.dumps([{"id": season.id, "number": season.number, "year": season.year,
                        "start": to_unix(season.start_time()),
                        "end": to_unix(season.end_time()) if season.end_date else to_unix(utcnow()),
                        "color": "#ff6666" if season.id % 2 == 0 else "#6666ff"}
                       for season in Season.objects.filter(id__gt=14, start_date__isnull=False).order_by('id')])

    
def get_season_list():
    """ Return season list as json. """
    return cache_value("season_list", 600, _get_season_list)


def _last_updated_info():
    max_cache = Cache.objects.all().aggregate(Max('created'))
    max_ranking = Ranking.objects.all().aggregate(Max('data_time'), Max('season'))
    return min(max_cache['created__max'], max_ranking['data_time__max']).date().isoformat(), max_ranking['season__max']

    
def last_updated_info():
    """ Return the date (data, season_id) was last updated. """
    return cache_value("last_updated_info", 600, _last_updated_info)
    

class BadRequestException(Exception):
    pass


class RankingsViewClient(object):

    def __init__(self):
        self.cpp = None

    def __call__(self, func, *args):
        try:
            if self.cpp is None:
                self.cpp = sc2.Get(settings.DATABASES['default']['NAME'],
                                   Enums.INFO,
                                   SEASON_FILTER)
            return getattr(self.cpp, func)(*args)
        except:
            self.cpp = None
            raise

    def close(self):
        self.cpp = None
        gc.collect()

            
class Nav(object):
    """ Nav helper. """
    
    def __init__(self, request, title=None, levels=-1):
        """ Level is significant levels (/-separated) in the url, 0 is infinite. """
        self.request = request
        self.items = []
        self.levels = levels
        self.title = title

    def add(self, heading, href='#', tooltip='', clazz=""):
        if self.levels != -1:
            h = href
            if self.levels != 0:
                h = '/'.join(h.split('/')[:self.levels + 1])
            clazz += " visiting" if self.request.path.startswith(h) else ""
        self.items.append((heading, href, clazz, tooltip))
        return self
        
    def __iter__(self):
        return iter(self.items)


class MainNavMixin(object):
    """ Adds the common main nav to a view and various other things. """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_nav'] = Nav(self.request, levels=1) \
            .add('LADDER',
                 reverse('ladder', kwargs={'version': Version.DEFAULT_KEY,
                                           'mode': Mode.DEFAULT_KEY,
                                           'reverse': '',
                                           'sort_key': DEFAULT_SORT_KEY}),
                 'Current ladder.') \
            .add('STATS',
                 reverse('stats:leagues', kwargs={'mode_key': Mode.DEFAULT_KEY}),
                 'Ladder statistics over time.') \
            .add('CLANS',
                 reverse('clan-overview'),
                 'Clan ladders.') \
            .add('DONATE',
                 reverse('donate'),
                 'Donate.') \
            .add('NEWS',
                 reverse('news'),
                 'News about this site.') \
            .add('ABOUT',
                 reverse('about'),
                 'About this site.')
        return context
    

class CachingRedirectView(RedirectView):

    @cache_control('max-age=86400')
    def get(self, request):
        return super().get(request)


class CachingTemplateView(MainNavMixin, TemplateView):
    
    @cache_control('max-age=86400')
    def get(self, request, **kwargs):
        return super().get(request, **kwargs)
    
        
rankings_view_client = RankingsViewClient()


