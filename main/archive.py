import os
import json
import gzip

from django.db import transaction
from logging import getLogger
from datetime import timedelta

from common.settings import config
from main.models import Cache, Ranking
from common.logging import log_context

logger = getLogger('django')


class BreakRun(Exception):

    pass


class DataArchiver(object):
    
    def __init__(self, now, dir=None, remove=False):
        self._stop = False
        self.now = now
        self.remove = remove
        if dir is None:
            self.dir = config.DATA_DIR
        else:
            self.dir = dir

    def stop(self):
        self._stop = True
        
    def archive_ranking(self, ranking, check_stop=lambda: None):
        """ Archive ranking. """
        with transaction.atomic():
    
            if self.remove:
                filename = "/dev/null"
            else:
                filename = "%s/archive-ranking-%d.gz" % (self.dir, ranking.id)
    
            with gzip.open(filename, mode='wb') as file:
        
                caches = ranking.sources
        
                logger.info("archiving ranking %d (%d caches) to %s" % (ranking.id, caches.count(), filename))
        
                check_stop()
        
                # Store metadata json on first line.
                struct = dict(
                    version=1,
                    ranking_id=ranking.id,
                    season_id=ranking.season_id,
                    created=ranking.created.isoformat(),
                    data_time=ranking.data_time.isoformat(),
                    min_data_time=ranking.min_data_time.isoformat(),
                    max_data_time=ranking.max_data_time.isoformat(),
                )
                s = json.dumps(struct, allow_nan=False)
                file.write(s.encode('utf-8'))
                file.write(b'\n')
        
                for obj in caches.all():
            
                    check_stop()
            
                    struct = dict(
                        id=obj.id,
                        url=obj.url,
                        region=obj.region,
                        bid=obj.bid,
                        type=obj.type,
                        status=obj.status,
                        created=obj.created.isoformat(),
                        updated=obj.updated.isoformat(),
                        data=json.loads(obj.data),
                    )
                    s = json.dumps(struct, allow_nan=False)
                    file.write(s.encode('utf-8'))
                    file.write(b'\n')
        
                # Do the actual removes.
        
                caches.all().delete()
    
            # Mark ranking as without data after closing the file but before completing the transation.
    
            ranking.status = Ranking.COMPLETE_WITOUT_DATA
            ranking.save()
        
    @log_context(feature='arch')
    def archive_rankings(self, check_stop=lambda: None):
        """ Archive cache data for all rankings older than 100 days, save each ranking in a data dir file. """

        with transaction.atomic():
            rankings = Ranking.objects.filter(data_time__lt=self.now - timedelta(days=100),
                                              status=Ranking.COMPLETE_WITH_DATA).order_by('id')

        for ranking in rankings:
            self.archive_ranking(ranking, check_stop=check_stop)

    @log_context(feature='arch')
    def load_ranking_archive(self, filename):
        """ This method is mostly for testing, it will read the caches in the files into memory. """

        with gzip.open(filename, mode='rb') as file:

            # Skip header row.
            header = json.loads(next(file).decode('utf-8'))

            ranking_id = header['ranking_id']

            try:
                Ranking.objects.get(id=ranking_id)
            except Ranking.DoesNotExist:
                ranking_id = None

            for row in file:
                struct = json.loads(row.decode('utf-8'))
                struct['data'] = json.dumps(struct['data'], indent=4)
                struct['ranking_id'] = ranking_id
                Cache.objects.create(**struct)
