# See comment in aid.test.base.

from django import setup
from django.conf import settings

from rocky import syspath

syspath.add('../..', __file__)
syspath.add('../../site', __file__)

from common.settings import site_settings

test_settings = site_settings()
test_settings['DATABASES']['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
settings.configure(**test_settings)
setup()
