from rocky import syspath
from django.conf import settings
from django.core.wsgi import get_wsgi_application

syspath.add('..', __file__)

from common.settings import site_settings

if not settings.configured:
    settings.configure(**site_settings())

application = get_wsgi_application()
