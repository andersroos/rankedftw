import random
from django.shortcuts import render
from common.cache import cache_control
from main.models import Mode, Version

from main.views.base import CachingTemplateView, SORT_KEYS
from django.core.urlresolvers import reverse


@cache_control('max-age=86400')
def sitemap_view(request):
    context = {}

    context['stats'] = ['stats:leagues', 'stats:population', 'stats:races']
    context['modes'] = [k for k in Mode.keys if k != Mode.UNKNOWN_KEY]
    context['versions'] = [k for k in Version.keys if k != Version.UNKNOWN_KEY]
    context['reverses'] = ['', '-']
    context['sort_keys'] = SORT_KEYS.keys()

    return render(request, 'sitemap.xml', context)


class MainView(CachingTemplateView):
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['team_link'] = random.choice([reverse('team', args=(333316,)),  # Catz
                                              reverse('team', args=(757622,)),  # Welmu
                                              reverse('team', args=(298031,)),  # Engineer
                                              ])
        return context
