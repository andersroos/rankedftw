from django import template
from django.conf import settings

from main.models import Region, Race, League, Version, Mode
from main.views.search import SearchView

register = template.Library()


@register.filter
def region_key(region_id):
    return Region.key_by_ids.get(region_id, Region.UNKNOWN_KEY)

    
@register.filter
def region_name(region_id):
    return Region.name_by_ids.get(region_id, Region.UNKNOWN_NAME)


@register.filter
def region_id(region_key):
    return Region.id_by_keys.get(region_key, Region.UNKNOWN_ID)


@register.filter
def region_image(region_id):
    region_key = Region.key_by_ids.get(region_id, Region.UNKNOWN_KEY)
    return (
        '<img class="region" srcset="'
        f'{settings.STATIC_URL}img/regions/{region_key}-16x16.webp 1.2x'
        f', {settings.STATIC_URL}img/regions/{region_key}-128x128.webp 2x'
        '" width="16px" height="16px"/>'
    )
    
    
@register.filter
def race_key(race_id):
    return Race.key_by_ids.get(race_id, Race.UNKNOWN_KEY)

    
@register.filter
def race_name(race_id):
    return Race.name_by_ids.get(race_id, Race.UNKNOWN_NAME)

    
@register.filter
def league_key(league_id):
    return League.key_by_ids.get(league_id, League.UNKNOWN_KEY)


@register.filter
def league_name(league_id):
    return League.name_by_ids.get(league_id, League.UNKNOWN_NAME)
    

@register.filter
def mode_name(mode):
    return Mode.name_by_ids.get(mode, Mode.UNKNOWN_NAME)
 

@register.filter
def mode_key(mode):
    return Mode.key_by_ids.get(mode, Mode.UNKNOWN_KEY)
   
    
@register.filter
def team_size(mode):
    return Mode.team_size(mode)
 

@register.filter
def version_name(version):
    return Version.name_by_ids.get(version, Version.UNKNOWN_NAME)
 

@register.filter
def version_key(version):
    return Version.key_by_ids.get(version, Version.UNKNOWN_KEY)
   
    
@register.filter
def tag_braces(tag):
    """ Put braces around tag if nonempty. """
    if tag:
        return "[%s]" % tag
    return tag


@register.filter
def format_win_rate(v):
    if v is None:
        return None
        
    return "%.1f%%" % v


@register.filter
def format_points(v):
    if v is None:
        return None
        
    return int(v)


@register.filter
def none_to_dash(v):
    if v is None:
        return '-'
        
    return v

    
@register.filter
def date_format(dt):
    """ Isoformat datetime. """
    return dt.date().isoformat()
    
    
@register.filter
def offset_to_page_number(offset):
    return int(offset / SearchView.PAGE_SIZE) + 1
    
    
