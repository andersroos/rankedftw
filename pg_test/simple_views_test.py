import aid.test.init_django_postgresql

from aid.test.db import Db
from aid.test.base import DjangoTestCase
from django.test import Client


class Test(DjangoTestCase):

    @classmethod
    def setUpClass(self):
        super(Test, self).setUpClass()
        self.db = Db()

    def setUp(self):
        super().setUp()
        self.c = Client()

    def test_main_page(self):
        response = self.c.get('/')
        self.assertEqual(200, response.status_code)

    def test_donate_page(self):
        response = self.c.get('/donate/')
        self.assertEqual(200, response.status_code)

    def test_about_page(self):
        response = self.c.get('/about/')
        self.assertEqual(200, response.status_code)

    def test_news_page(self):
        response = self.c.get('/news/')
        self.assertEqual(200, response.status_code)

    def test_sitemap(self):
        response = self.c.get('/sitemap.xml')
        self.assertEqual(200, response.status_code)

