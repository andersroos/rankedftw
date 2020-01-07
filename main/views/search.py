import json
import re
from logging import getLogger

from django.http import Http404, HttpResponse
from django.urls import reverse

from django.views.generic.base import TemplateView

from main.battle_net import get_bnet_profile_url_info, BnetClient
from main.views.base import MainNavMixin, last_updated_info
from django.shortcuts import redirect
from django.db.models import Q
from common.cache import cache_control
from main.models import Player, Team, Mode, Region, League, Version, Race


logger = getLogger('django')


def get_bnet_url(player):
    return f"https://starcraft2.com/en-gb/profile/{BnetClient.REGION_IDS[player.region]}/{player.realm}/{player.bid}"


class SearchView(MainNavMixin, TemplateView):

    PAGE_SIZE = 32

    @cache_control("max-age=3600")
    def get(self, request):
        
        context = self.get_context_data()

        json_response = 'json' in request.GET

        name = request.GET.get('name', '').strip()
        context['name'] = name

        try:
            offset = max(int(request.GET.get('offset', 0)), 0)
        except ValueError:
            offset = 0
        
        if not json_response:

            region, realm, bid = get_bnet_profile_url_info(name)

            if region is not None:
                # Treat this as a battle net url.
                try:
                    # Go directly to the player page if found.
                    player = Player.non_purged.get(bid=bid, realm=realm, region=region)
                    return redirect('player', player_id=player.id)
                except Player.DoesNotExist:
                    # Return no match.
                    context['items'] = None
                    return self.respond(context, False)

        # Limit name to at least on char.

        if not name or len(name) < 2:
            context['no_search'] = True
            return self.respond(context, json_response)

        # Try to search for player. (Only db index on start or exact.)

        q = Player.non_purged.filter(name__istartswith=name).order_by('-season', 'mode', 'name', 'region', 'bid')
        
        items = q[offset:offset + self.PAGE_SIZE + 1]
        
        if len(items) == 0 or len(items) > self.PAGE_SIZE:
            count = q.count()
        else:
            count = len(items) + offset
            
        pages = list(range(max(offset - self.PAGE_SIZE * 6, 0), count, self.PAGE_SIZE))[:12]

        if offset == 0:
            context['prev'] = None
        else:
            context['prev'] = offset - self.PAGE_SIZE

        if pages and offset == pages[-1]:
            context['next'] = None
        else:
            context['next'] = offset + self.PAGE_SIZE

        context['count'] = count
        context['page_size'] = self.PAGE_SIZE
        context['items'] = items[:self.PAGE_SIZE]
        context['pages'] = pages
        context['offset'] = offset
            
        return self.respond(context, json_response)

    def respond(self, context, json_response):
        if not json_response:
            return self.render_to_response(context)

        if context.get('no_search', False):
            data = {'count': -1}
        else:
            data = {
                'count': context['count'],
                'offset': context['offset'],
                'items': [{
                    'name': p.name,
                    'tag': p.tag,
                    'clan': p.clan,
                    'mode': Mode.key_by_ids.get(p.mode, Mode.UNKNOWN_KEY),
                    'league': League.key_by_ids.get(p.league,  League.UNKNOWN_KEY),
                    'race': Race.key_by_ids.get(p.race,  Race.UNKNOWN_KEY),
                    'region': Region.key_by_ids.get(p.region,  Region.UNKNOWN_KEY),
                    'bnet_url': get_bnet_url(p),
                    'season': p.season_id,
                } for p in context.get('items', [])],
            }
        return HttpResponse(json.dumps(data, indent=2), content_type="application/json", status=200)


class PlayerView(MainNavMixin, TemplateView):
    
    @cache_control("max-age=3600")
    def get(self, request, player_id=None):
        player_id = int(player_id)
        
        context = self.get_context_data()

        try:
            player = Player.non_purged.get(id=player_id)
        except Player.DoesNotExist:
            raise Http404('Could not find player %d.' % player_id)

        teams = Team.non_purged\
            .filter(Q(member0=player) | Q(member1=player) | Q(member2=player) | Q(member3=player))\
            .select_related('member0', 'member1', 'member2', 'member3')\
            .order_by('mode', '-league')

        context['player'] = player
        context['bnet_url'] = get_bnet_url(player)
        context['teams'] = teams

        _, season_id = last_updated_info()
        
        for team in teams:
            if team.season_id == season_id:
                team.ladder_url \
                    = reverse('ladder',
                              kwargs={'version': Version.key_by_ids.get(team.version, Version.DEFAULT),
                                      'mode': Mode.key_by_ids[team.mode],
                                      'reverse': '',
                                      'sort_key': 'ladder-rank'})\
                    + "?team=%d" % team.id
                              
        return self.render_to_response(context)


