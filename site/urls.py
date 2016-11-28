from django.conf.urls import include, url
from logging import INFO
from django.core.urlresolvers import reverse_lazy

from common.settings import config
from main.views.clan import ClanOverviewView, ClanView
from main.views.team import TeamView, TeamRankingsData, TeamSeasonsData, TeamId
from main.views.search import SearchView, PlayerView
from main.views.stats import StatsRaw, StatsView
from main.views.main import MainView, sitemap_view
from main.views.ladder import LadderView
from main.views.base import CachingTemplateView, CachingRedirectView
from main.models import Mode


urlpatterns = \
    [
        url(r'^$', MainView.as_view(template_name='main.html'), name='main'),

        url(r'^search/$', SearchView.as_view(template_name='search.html'), name='search'),

        url(r'^team/(?P<team_id>\d+)/$', TeamView.as_view(template_name='team.html'), name='team'),

        url(r'^team/(?P<team_id>\d+)/rankings/$', TeamRankingsData.as_view()),

        url(r'^team/id/$', TeamId.as_view()),

        url(r'^team/seasons/$', TeamSeasonsData.as_view()),

        url(r'^ladder/(?P<version>\w+)'
            '/(?P<mode>[\w-]+)'
            '/(?P<reverse>-?)(?P<sort_key>[\w-]+)/$',
            LadderView.as_view(template_name='ladder.html'),
            name='ladder'),

        url(r'^clan/$', ClanOverviewView.as_view(template_name='clan-overview.html'), name='clan-overview'),

        url(r'^clan/(?P<tag>[\w-]+)/(?P<reverse>-?)(?P<sort_key>[\w-]+)/$',
            ClanView.as_view(template_name='clan.html'), name='clan'),

        url(r'^player/(?P<player_id>\d+)/$', PlayerView.as_view(template_name='player.html'), name='player'),

        url(r'^about/$', CachingTemplateView.as_view(template_name='about.html'), name='about'),

        url(r'^donate/$', CachingTemplateView.as_view(template_name='donate.html'), name='donate'),

        url(r'^news/$', CachingTemplateView.as_view(template_name='news.html'), name='news'),

        url(r'sitemap\.xml$', sitemap_view),

        url(r'^stats/', include([

            url(r'^$',
                CachingRedirectView.as_view(url=reverse_lazy('stats:leagues', kwargs={'mode_key': Mode.DEFAULT_KEY})),
                name='main'),

            url(r'^leagues/$',
                CachingRedirectView
                .as_view(url=reverse_lazy('stats:leagues', kwargs={'mode_key': Mode.DEFAULT_KEY})),
                name='leagues-default'),

            url(r'^leagues/(?P<mode_key>[\w-]+)/$',
                StatsView.as_view(template_name='stats-leagues.html'),
                name='leagues'),

            url(r'^population/$',
                CachingRedirectView
                .as_view(url=reverse_lazy('stats:population', kwargs={'mode_key': Mode.DEFAULT_KEY})),
                name='population-default'),

            url(r'^population/(?P<mode_key>[\w-]+)/$',
                StatsView.as_view(template_name='stats-population.html'),
                name='population'),

            url(r'^races/$',
                CachingRedirectView
                .as_view(url=reverse_lazy('stats:races', kwargs={'mode_key': Mode.DEFAULT_KEY})),
                name='races-default'),

            url(r'^races/(?P<mode_key>[\w-]+)/$',
                StatsView.as_view(template_name='stats-races.html'),
                name='races'),

            url(r'^raw/(?P<mode_id>\d+)/$',
                StatsRaw.as_view(),
                name='raw')

        ], namespace='stats')),
    ]


# This is the recommened way to do it.
config.log_cached(log_level=INFO)

