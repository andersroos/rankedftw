import aid.test.init_django_postgresql

from aid.test.base import DjangoTestCase
from main.models import RankingData, Ranking, Season, Cache, RankingStats
from common.utils import utcnow
from main.delete import DataDeleter


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.now = utcnow()
        self.today = self.now.today()

        self.s1 = self.db.create_season(id=1,
                                        start_date=self.date(days=-499),
                                        end_date=self.date(days=-300))
        self.s2 = self.db.create_season(id=2,
                                        start_date=self.date(days=-299),
                                        end_date=self.date(days=-100))
        self.s3 = self.db.create_season(id=3,
                                        start_date=self.date(days=-99),
                                        end_date=self.date(days=100))
        
    def setUp(self):
        super().setUp()
        self.db.delete_all(keep=[Season])

    @staticmethod
    def delete(keep_last=None, dry_run=None):
        dd = DataDeleter(dry_run=dry_run)
        dd.delete_rankings(keep_last=keep_last)
        dd.delete_cache_data()

    def test_unlinked_200_caches_older_than_30_days_are_removed(self):

        l = self.db.create_ladder()
        r = self.db.create_ranking()

        c1 = self.db.create_cache(ladder=None, ranking=None, status=200, updated=self.datetime(days=-29))
        c2 = self.db.create_cache(ladder=None, ranking=None, status=200, updated=self.datetime(days=-30))
        c3 = self.db.create_cache(ladder=None, ranking=None, status=200, updated=self.datetime(days=-31))
        c4 = self.db.create_cache(ladder=None, ranking=None, status=404, updated=self.datetime(days=-32))
        c5 = self.db.create_cache(ladder=l,    ranking=None, status=200, updated=self.datetime(days=-32))
        c6 = self.db.create_cache(ladder=None, ranking=r,    status=200, updated=self.datetime(days=-32))
        c7 = self.db.create_cache(ladder=l,    ranking=r,    status=404, updated=self.datetime(days=-29))

        self.delete(keep_last=0, dry_run=False)

        self.assertEqual({c1, c4, c5, c6, c7}, {c for c in Cache.objects.all()})

    def stats_ranking_data_and_cache_data_is_removed_together_with_ranking(self):

        rr1 = self.db.create_ranking(created=self.datetime(days=-400, minutes=1), season=self.s1)
        rd1 = self.db.create_ranking_data(ranking=rr1)
        rs1 = self.db.update_ranking_stats(ranking=rr1)

        rr2 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        rd2 = self.db.create_ranking_data(ranking=rr2)
        rs2 = self.db.update_ranking_stats(ranking=rr2)
        c1 = self.db.create_cache(rankign=rr2, status=200, updated=self.datetime(days=-32))
        c2 = self.db.create_cache(rankign=rr2, status=200, updated=self.datetime(days=-29))
        c3 = self.db.create_cache(rankign=rr2, status=200, updated=self.datetime(days=-32))

        rr3 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        rd3 = self.db.create_ranking_data(ranking=rr3)
        rs3 = self.db.update_ranking_stats(ranking=rr3)

        self.delete(keep_last=0, dry_run=False)

        self.assertEqual(2, len(self.db.all(Ranking)))
        self.assertEqual(2, len(self.db.all(RankingData)))
        self.assertEqual(2, len(self.db.all(RankingStats)))
        self.assertEqual(2, len(self.db.all(Cache)))

        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr2.id)
        self.assertRaises(RankingData.DoesNotExist, RankingData.objects.get, pk=rd2.id)
        self.assertRaises(RankingStats.DoesNotExist, RankingStats.objects.get, pk=rs2.id)
        self.assertRaises(Cache.DoesNotExist, Cache.objects.get, pk=c1.id)
        self.assertRaises(Cache.DoesNotExist, Cache.objects.get, pk=c2.id)

    def test_keep_with_intervals_of_7_days_from_kept(self):

        def create(days, minutes):
            return self.db.create_ranking(created=self.now,
                                          data_time=self.datetime(days=days, minutes=minutes),
                                          season=self.s1)

        rr1 = create(-400 + 0,  1)
        rr2 = create(-400 + 6,  2)
        rr3 = create(-400 + 7,  3)
        rr4 = create(-400 + 8,  4)
        rr5 = create(-400 + 14, 5)
        rr6 = create(-400 + 15, 6)
        rr7 = create(-400 + 16, 7)
        rr8 = create(-400 + 18, 8)
        rr9 = create(-400 + 21, 9)
        
        self.delete(keep_last=0, dry_run=False)

        self.assertEqual(4, len(self.db.all(Ranking)))
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr2.id)
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr4.id)
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr6.id)
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr7.id)
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr8.id)
        
    def test_keep_last_in_each_season(self):
        rr1 = self.db.create_ranking(created=self.datetime(days=-400, minutes=1), season=self.s1)
        rr2 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s2)
        rr3 = self.db.create_ranking(created=self.datetime(days=-200, minutes=3), season=self.s2)
        rr4 = self.db.create_ranking(created=self.datetime(days=-200, minutes=4), season=self.s3)
        rr5 = self.db.create_ranking(created=self.datetime(days=0,    minutes=5), season=self.s3)
        
        self.delete(keep_last=0, dry_run=False)

        self.assertEqual(3, len(self.db.all(Ranking)))
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr2.id)
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr4.id)
        
    def test_keep_last_7_rankings(self):
        rr1 = self.db.create_ranking(created=self.datetime(days=-400, minutes=1), season=self.s1)
        rr2 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        rr3 = self.db.create_ranking(created=self.datetime(days=-400, minutes=3), season=self.s1)
        rr4 = self.db.create_ranking(created=self.datetime(days=-400, minutes=4), season=self.s1)
        rr5 = self.db.create_ranking(created=self.datetime(days=-400, minutes=5), season=self.s1)
        rr6 = self.db.create_ranking(created=self.datetime(days=-400, minutes=6), season=self.s1)
        rr7 = self.db.create_ranking(created=self.datetime(days=-400, minutes=7), season=self.s1)
        rr8 = self.db.create_ranking(created=self.datetime(days=-400, minutes=8), season=self.s1)
        rr9 = self.db.create_ranking(created=self.datetime(days=-400, minutes=9), season=self.s1)
        
        self.delete(keep_last=7, dry_run=False)

        self.assertEqual(8, len(self.db.all(Ranking)))
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr2.id)

    def test_keep_first_ranking(self):
        rr1 = self.db.create_ranking(created=self.datetime(days=-400, minutes=1), season=self.s1)
        rr2 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        rr3 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        
        self.delete(keep_last=0, dry_run=False)

        self.assertEqual(2, len(self.db.all(Ranking)))
        self.assertRaises(Ranking.DoesNotExist, Ranking.objects.get, pk=rr2.id)

    def test_dry_run_does_not_delete(self):
        rr1 = self.db.create_ranking(created=self.datetime(days=-400, minutes=1), season=self.s1)
        rr2 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)
        rr3 = self.db.create_ranking(created=self.datetime(days=-400, minutes=2), season=self.s1)

        c1 = self.db.create_cache(status=200, ladder=None, ranking=None, updated=self.datetime(days=-32))

        self.delete(keep_last=0, dry_run=True)

        self.assertEqual(3, len(self.db.all(Ranking)))
        self.assertEqual(1, len(self.db.all(Cache)))
