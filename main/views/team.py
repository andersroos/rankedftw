
import json

from django.views.generic.base import TemplateView, View

from main.battle_net import get_bnet_profile_url_info
from main.models import Team, League, Version, Mode, Player
from common.cache import cache_control
from django.http import Http404
from main.views.base import rankings_view_client, MainNavMixin, get_season_list, last_updated_info, BadRequestException
from django.http import HttpResponse
from django.core import urlresolvers


class TeamView(MainNavMixin, TemplateView):
    
    @cache_control("max-age=3600")
    def get(self, request, team_id=None):
        team_id = int(team_id)
        
        context = self.get_context_data()

        try:
            team = Team.objects.select_related('member0', 'member1', 'member2', 'member3').get(id=team_id)
            context['team'] = team
        except Team.DoesNotExist:
            raise Http404('Could not find team %d.' % team_id)

        context['members'] = [m for m in [team.member0, team.member1, team.member2, team.member3] if m]
        context['leagues'] = [League.name_by_ids[i] for i in range(League.BRONZE, League.GRANDMASTER + 1)]
        context['seasons'] = get_season_list()
        context['last_updated'], season_id = last_updated_info()

        if team.season_id == season_id:
            url = urlresolvers.reverse('ladder',
                                       kwargs={'version': Version.key_by_ids.get(team.version),
                                               'mode': Mode.key_by_ids[team.mode],
                                               'reverse': '',
                                               'sort_key': 'ladder-rank'})\
                + "?team=%d" % team.id
            context['ladder_href'] = url
        
        return self.render_to_response(context)
        

class TeamRankingsData(View):
    
    @cache_control("max-age=3600")
    def get(self, request, team_id=None):
        team_id = int(team_id)
        rankings = rankings_view_client('rankings_for_team', team_id)
        return HttpResponse(json.dumps(rankings), content_type="application/json", status=200)

        
class TeamSeasonsData(View):
    
    @cache_control("max-age=3600")
    def get(self, request):
        return HttpResponse(get_season_list(), content_type="application/json", status=200)

    
class TeamId(View):

    @staticmethod
    def get_player(url):
        if not url:
            raise BadRequestException("empty battle net profile url")

        region, realm, bid = get_bnet_profile_url_info(url)
        if region is None:
            raise BadRequestException("could not find region from player '%s'" % url)

        try:
            return Player.objects.get(region=region, realm=realm, bid=bid)
        except Player.DoesNotExist:
            raise Http404("could not find player using '%s'" % url)

    @cache_control("max-age=3600")
    def get(self, request):
        try:
            mode = request.GET.get('mode', '').strip()
            mode_id = Mode.id_by_keys.get(mode, Mode.UNKNOWN_ID)
            if mode_id == Mode.UNKNOWN_ID:
                raise BadRequestException("uknown mode '%s'" % mode)

            players = sorted((self.get_player(url) for url in request.GET.getlist('player')), key=lambda p: p.id)

            if len(players) != Mode.team_size(mode_id):
                raise BadRequestException("team size and player count mismatch")

            players.extend([None, None, None])

            try:
                team = Team.objects.get(mode=mode_id, member0=players[0], member1=players[1], member2=players[2],
                                        member3=players[3])
                return HttpResponse(json.dumps({'team_id': team.id}), content_type="application/json", status=200)
            except Team.DoesNotExist:
                raise Http404("could not find team")

        except Http404 as e:
            return HttpResponse(json.dumps({'message': str(e)}), content_type="application/json", status=404)

        except BadRequestException as e:
            return HttpResponse(json.dumps({'message': str(e)}), content_type="application/json", status=400)
