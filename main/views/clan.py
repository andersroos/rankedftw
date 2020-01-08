import json
from copy import copy
from logging import getLogger

from django.db.models import Count
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from common.cache import cache_control, cache_value
from main.client import client, ClientError
from main.models import Season, Player, Mode, Team, Region, League, Race
from main.views.base import MainNavMixin, DEFAULT_SORT_KEY
from main.views.ladder import LadderCommon
from main.views.search import get_bnet_url

logger = getLogger('django')


def clan_url(request, paths=None, args=None, name=None, key=None, tag=None):

    if name in paths:
        paths = copy(paths)
        paths[name] = key

    url = reverse(request.resolver_match.view_name, kwargs=paths)

    if name in args:
        args = copy(args)
        args[name] = key

    filters = [v for k, v in args.items() if v is not None and v != Region.ALL_KEY]
    if filters:
        url += '?f=%s' % ','.join(filters)

    return url


def get_top_clans():
    current_season = Season.get_current_season()
    return list(Player.objects
                .filter(season=current_season, mode=Mode.TEAM_1V1, tag__gt='')
                .values('clan', 'tag').annotate(count=Count('tag')).order_by('-count')[:32])


class ClanOverviewView(MainNavMixin, TemplateView):

    @cache_control("max-age=3600")
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()

        current_season = Season.get_current_season()

        clan = request.GET.get('clan', None)
        if clan is None:
            context['clans'] = cache_value("top_clans", 1200, get_top_clans)
        else:
            clan = clan.strip()
            context['search'] = True

            clans = list(Player.objects
                         .filter(season=current_season,
                                 mode=Mode.TEAM_1V1,
                                 tag__gt='')
                         .filter(Q(clan__istartswith=clan) | Q(tag__istartswith=clan))
                         .values('clan', 'tag').annotate(count=Count('tag')).order_by('-count')[:33])

            if len(clans) == 33:
                clans = clans[:32]
                context['left_out'] = True

            clans.sort(key=lambda c: c['clan'])

            if len(clans) == 1:
                return redirect('clan', tag=clans[0]['tag'], reverse='', sort_key=DEFAULT_SORT_KEY)

            context['clans'] = clans

        return self.render_to_response(context)


class ClanView(MainNavMixin, TemplateView, LadderCommon):

    @staticmethod
    def fetch_data(tag, sort_key_id, is_reverse=None, league_id=None, region_id=None, race_id=None):

        # Get ids from db.

        teams = {t.id: t for t in
                 Team.objects
                 .filter(member0__tag=tag, mode=Mode.TEAM_1V1, season=Season.get_current_season())
                 .all()
                 .select_related('member0')}

        # Fetch data from server.

        data = client.get_clan(team_ids=list(teams.keys()), key=sort_key_id, reverse=is_reverse,
                               region=region_id, race=race_id, league=league_id)

        # Fetch information about teams from database.

        team_ranks = data['teams']

        for tr in team_ranks:
            # TODO Make common with ladder to make less error prone?
            t = teams[tr["team_id"]]
            tr['rank'] += 1
            tr['tier'] += 1
            tr["m0_id"] = t.member0.id
            tr["m0_name"] = t.member0.name
            tr["m0_bnet_url"] = get_bnet_url(t.member0)

        return data

    @cache_control("max-age=3600")
    def get(self, request, *args, tag=None, reverse=None, sort_key=None, **kwargs):
        
        if sort_key == 'ladder-rank':
            return redirect(self.redirect_mmr_url(request, 'clan', tag=tag, reverse=reverse))
        
        context = self.get_context_data()

        json_response = 'json' in request.GET

        if tag is None:
            raise Http404()

        region_id, race_id, league_id = self.extract_filters(request)
        is_reverse, sort_key_id = self.extract_common(reverse, sort_key)

        player = Player.objects.filter(tag=tag, mode=Mode.TEAM_1V1, season=Season.get_current_season()).first()
        if not player:
            raise Http404()

        context['tag'] = tag
        context['clan'] = player.clan

        try:
            data = self.fetch_data(tag, sort_key_id, is_reverse=is_reverse,
                                   league_id=league_id, region_id=region_id, race_id=race_id)
        except ClientError as e:
            logger.exception("Fetch from client error: %s" % str(e))
            context['error'] = 'The server is not feeling well, try again later.'
            return self.respond(context, json_response)

        LadderCommon.update_age(data)

        context['ladder'] = data
        context['team_size'] = 1

        paths = {
            'tag': tag,
            'sort_key': sort_key,
            'reverse': reverse,
        }

        args = {
            'region': Region.key_by_ids.get(region_id, Region.ALL_KEY),
            'league': League.key_by_ids.get(league_id),
            'race': Race.key_by_ids.get(race_id),
        }

        values = [('All', None)] + [(Race.name_by_ids[i], Race.key_by_ids[i])
                                    for i in Race.ids if i != Race.UNKNOWN]
        LadderCommon.set_nav(context, request, clan_url, paths, args, name='race', values=values)

        values = [('All', None)] + [(League.name_by_ids[i], League.key_by_ids[i])
                                    for i in League.ids if i not in (League.UNKNOWN, League.ALL)]
        LadderCommon.set_nav(context, request, clan_url, paths, args, name='league', values=values)

        values = [(Region.name_by_ids[i], Region.key_by_ids[i])
                  for i in Region.ids if i != Region.UNKNOWN]
        LadderCommon.set_nav(context, request, clan_url, paths, args, name='region', values=values)

        values = [('MMR', 'mmr'), ('League points', 'league-points'), ('Games played', 'played'), ('Wins', 'wins'),
                  ('Losses', 'losses'), ('Win rate', 'win-rate')]
        LadderCommon.set_nav(context, request, clan_url, paths, args, name='sort_key', values=values)

        context['reverse_visiting'] = 'visiting' if reverse else ''
        context['reverse_href'] = clan_url(request, paths, args, 'reverse', '' if reverse else '-')

        return self.respond(context, json_response)

    def respond(self, context, json_response):
        if not json_response:
            return self.render_to_response(context)

        if 'error' in context:
            return HttpResponse(context['error'], status=500)

        teams = context['ladder']['teams']
        for team in teams:
            team['m0_race'] = Race.key_by_ids[team['m0_race']]
            team['league'] = League.key_by_ids[team['league']]
            team['region'] = Region.key_by_ids[team['region']]
            del team['m0_id']
            del team['m1_race']
            del team['m2_race']
            del team['m3_race']

        return HttpResponse(json.dumps(context['ladder']['teams'], indent=2),
                            content_type="application/json",
                            status=200)
