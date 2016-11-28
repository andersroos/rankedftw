from django.conf import settings
from django import setup
from rocky import syspath

syspath.add('..', __file__)

try:
    from lib import sc2
    from logging import getLogger
    sc2.set_logger(getLogger("django"))
except:
    pass

from common.settings import tasks_settings
settings.configure(**tasks_settings())
setup()

