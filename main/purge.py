from logging import getLogger

from common.utils import utcnow, api_data_purge_date, to_unix
from lib import sc2
from main.models import Ranking, get_db_name, Team, Player

logger = getLogger('django')
sc2.set_logger(logger)


def purge_player_data(check_stop=lambda: None):
    rankings = list(
        Ranking.objects.filter(status__in=(Ranking.COMPLETE_WITH_DATA, Ranking.COMPLETE_WITOUT_DATA)).order_by('id')
    )
    
    cpp_purger = sc2.Purger(get_db_name())
    
    for ranking in rankings[:-1]:
        if check_stop():
            return
        
        cpp_purger.purge_removed_teams_from_ranking(ranking.id, to_unix(utcnow()), api_data_purge_date().isoformat())
        
    Team.all_objects.filter(last_seen__lt=api_data_purge_date()).delete()
    Player.all_objects.filter(last_seen__lt=api_data_purge_date()).delete()
