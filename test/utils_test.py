import aid.test.init_django_sqlite

from aid.test.base import DjangoTestCase
from common.utils import human_t_short, human_f_short, human_i_split


class Test(DjangoTestCase):

    def test_time_formatting(self):
        self.assertEqual("1.00s", human_t_short(1))
        self.assertEqual("10.12ms", human_t_short(0.01012))
        self.assertEqual("2.33us", human_t_short(0.00000233))
        self.assertEqual("2.50m", human_t_short(150))
        self.assertEqual("2.00h", human_t_short(7200))

    def test_number_formatting(self):
        self.assertEqual("10.55M", human_f_short(1.055e7))
        self.assertEqual("10.00m", human_f_short(0.01))
        
    def test_number_splitting(self):
        self.assertEqual("12 345 600", human_i_split(1.23456e7))
