import sys
from copy import copy

from logging import INFO
from os import environ
from os.path import join, basename, abspath, dirname, exists
from rocky.config import PyFile, Config, Env, FileContent

topdir = abspath(join(dirname(__file__), '..'))


DEV_SECRET_KEY = 'change-me-in-prod'


env = Env()
local_py = PyFile(join(dirname(__file__), '../local.py'), fail_on_not_found=False)
config_py = PyFile('/etc/rankedftw.py', fail_on_not_found=False)

config = Config(env, local_py, config_py, log_level=INFO)


def common_settings():

    config.get('INSTALL_DIR', default='/usr/local/rankedftw')
    config.get('PROD', default=True)

    config.get('LOG_DIR', default=join(config.INSTALL_DIR, 'log'))
    config.get('DATA_DIR', default=join(config.INSTALL_DIR, 'data'))
    config.get('CONF_DIR', default=join(config.INSTALL_DIR, 'etc'))
    config.get('PID_DIR', default=join(config.INSTALL_DIR, 'run'))

    config.get('DEBUG', env, local_py, default=not config.PROD)
    config.get('DB_DEBUG', default=False)

    config.get('API_KEY', log_value=False)
    config.get('API_SECRET', log_value=False)
    config.get('ACCESS_TOKEN', FileContent(join(config.CONF_DIR, 'access_token')), log_value=False)
    
    config.get('KEEP_API_DATA_DAYS', env, default="14")

    #
    # Django settings.
    #

    settings = {
        'USE_TZ': True,
        'TIME_ZONE': 'UTC',
        'CONN_MAX_AGE': None,
        'DEBUG': config.DEBUG,
        'DEBUG_TEMPLATE': config.get('DEBUG_TEMPLATE', env, local_py, default=not config.PROD),
        'SECRET_KEY': config.get('SECRET_KEY', default=DEV_SECRET_KEY, log_value=False),
        'ALLOWED_HOSTS': config.get('ALLOWED_HOSTS', local_py, config_py, default='*'),
        'DATABASES': {'default': copy(config.get('DEFAULT_DB', local_py, config_py,
                                                 default={'ENGINE': 'django.db.backends.postgresql_psycopg2',
                                                          'NAME': 'rankedftw',
                                                          'USER': environ.get('USER'),
                                                          'HOST': ''}))},
    }

    if config.PROD and config.SECRET_KEY == DEV_SECRET_KEY:
        raise Exception("set secret key in config, can't be default in prod")

    #
    # Additional settings.
    #

    config.get('VERSION', FileContent(config.INSTALL_DIR + '/deploy/version'), default='')

    return settings


def logging_settings(log_filename=None, log_stderr=False):
        handlers = {}

        if log_filename and exists(dirname(log_filename)):
            handlers['file'] = {'level': 'DEBUG' if config.DB_DEBUG else 'INFO',
                                'class': 'logging.handlers.WatchedFileHandler',
                                'filename': log_filename,
                                'formatter': 'default'}

        if log_stderr:
            handlers['console'] = {'level': 'DEBUG' if config.DB_DEBUG else 'INFO',
                                   'class': 'logging.StreamHandler',
                                   'stream': sys.stderr,
                                   'formatter': 'default'}

        return {'version': 1,
                'disable_existing_loggers': False,
                'formatters': {'default': {'()': 'common.logging.formatterFactory'}},
                'handlers': handlers,
                'loggers': {'root': {'level': 'INFO',
                                     'handlers': handlers.keys()},

                            'django': {'level': 'INFO',
                                       'propagate': False,
                                       'handlers': handlers.keys()},

                            'rocky': {'level': 'INFO',
                                      'propagate': False,
                                      'handlers': handlers.keys()},

                            # Prevent 404 to be logged as warning.
                            'django.request': {'level': 'ERROR',
                                               'propagate': False,
                                               'handlers': handlers.keys()},

                            'django.db.backends': {'level': 'DEBUG' if config.DB_DEBUG else 'INFO',
                                                   'propagate': False,
                                                   'handlers': handlers.keys()}}}


def tasks_settings():
    settings = common_settings()

    settings['LOGGING'] = \
        logging_settings(log_filename=join(config.LOG_DIR, basename(sys.argv[0]).replace('.py', '.log')),
                         log_stderr=True)

    settings['INSTALLED_APPS'] = ('main',)

    return settings


def site_settings():

    settings = common_settings()

    settings['LOGGING'] = \
        logging_settings(log_filename=join(config.LOG_DIR, 'site.log'),
                         log_stderr=config.DEBUG)

    settings['STATIC_ROOT'] = config.INSTALL_DIR + '/static' + ('/' + config.VERSION if config.VERSION else '')

    settings['STATIC_URL'] = '/static' + ('/' + config.VERSION if config.PROD else '') + '/'

    settings['STATICFILES_DIRS'] = (topdir + '/site/static',)

    settings['STATICFILES_FINDERS'] = ('django.contrib.staticfiles.finders.FileSystemFinder',)

    if config.DEBUG_TEMPLATE:
        loaders = ('django.template.loaders.filesystem.Loader',)
    else:
        loaders = [
            ('django.template.loaders.cached.Loader', ('django.template.loaders.filesystem.Loader',)),
        ]

    settings['TEMPLATES'] = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                topdir + '/site/templates',
            ],
            'APP_DIRS': False,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                    "django.template.context_processors.debug",
                    "django.template.context_processors.static",
                    "context_processors.site"
                ],
                'loaders': loaders,
                'debug': config.DEBUG_TEMPLATE,
            },
        },
    ]

    settings['MIDDLEWARE_CLASSES'] = (
        # Outer (Network)
        'main.middleware.CacheControlMiddleware',
        'django.middleware.common.CommonMiddleware',
        # Inner (View)
    )

    settings['ROOT_URLCONF'] = 'urls'

    settings['WSGI_APPLICATION'] = 'wsgi.application'

    settings['INTERNAL_IPS'] = ('127.0.0.1',)

    settings['INSTALLED_APPS'] = (
        'django.contrib.contenttypes',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'main',
    )

    return settings
