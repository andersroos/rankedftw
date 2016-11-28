# See comment in aid.test.base.

from django import setup
from django.conf import settings

from rocky import syspath

syspath.add('../..', __file__)
syspath.add('../../site', __file__)

if not settings.configured:

    from common.utils import uniqueid
    from common.settings import site_settings

    test_settings = site_settings()
    test_settings['DATABASES']['default']['NAME'] = 'rankedftw-' + uniqueid(6)
    settings.configure(**test_settings)
    setup()
