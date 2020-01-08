import string
from datetime import datetime, timedelta
from random import choice
from threading import Thread

from django.utils import timezone

epoch = datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)


# NOTE: This constant needs to be the same in c++-code.
KEEP_API_DATA_DAYS = 21


def utcnow(**kwargs):
    """ Get a timezone aware datetime, UTC now. """
    return datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(**kwargs)


def localnow():
    """ Get the current datetime in the local timezone for the user
    (timezone set by timezone.activate())."""
    return timezone.localtime(utcnow(), timezone=timezone.get_current_timezone())


def date_to_datetime_utc(d, hour=0, minute=0, second=0, microsecond=0):
    return datetime(d.year, d.month, d.day, hour, minute, second, microsecond, timezone.utc)
    

def to_unix(dt):
    """ Convert datetime to unix time. """
    return (dt - epoch).total_seconds()


def from_unix(unix):
    """ Convert unix time in utc to datetime to. """
    return datetime.utcfromtimestamp(unix).replace(tzinfo=timezone.utc)


def utctoday(**kwargs):
    """ Get date in UTC right now. """
    return utcnow().date() + timedelta(**kwargs)


def localtoday():
    """ Get the current date in the local timezone for the user
    (timezone set by timezone.activate())."""
    return timezone.localtime(utcnow(), timezone=timezone.get_current_timezone()).date()


def api_data_purge_date():
    """ Return the date when api data from this date needs to be purged due to Blizzard API terms of use. Terms says
    30 days, but need some margin to have time to purge. """
    return utctoday() - timedelta(days=KEEP_API_DATA_DAYS)


def uniqueid(length=12):
    return ''.join(choice(string.ascii_letters + string.digits + "_-") for _ in range(length))


def merge_args(*args, **kwargs):
    """ Merge args into a dict with update then apply kwargs to that dict. Path separator will be __. Kwargs will be
    applied in order. A path can create dicts on the path but will not overwrite values.

    Example:
        merge_args({'a': 1}, a=2)                          => {'a': 2}
        merge_args({'a': {'b': 2}, 'b': 3}, a__b=10, b=1)  => {'a': {'b': 10}, 'b': 1}
        merge_args({'a': 3}, a={'b': 1}, a__b=4)           => {'a': {'b': 4}}
        merge_args({}, a__b=3)                             => {'a': {'b': 3}}
        merge_args({'a': 3}, a__b=3)                       => FAIL
    """
    res = {}
    for arg in args:
        res.update(arg)

    def set_val(obj, p, v):
        if len(p) > 1:
            obj = obj.setdefault(p[0], {})
            set_val(obj, p[1:])
        else:
            obj[p[0]] = v

    for key, val in kwargs.items():
        path = key.split('__')
        set_val(res, path, val)

    return res


_n_suffixes = ((1e12, 'T'),
               (1e9, 'G'),
               (1e6, 'M'),
               (1e3, 'k'),
               (1e-0, ''),
               (1e-3, 'm'),
               (1e-6, 'u'),
               (1e-9, 'n'))

_t_suffixes = ((24 * 3600, 'd'),
               (3600, 'h'),
               (60, 'm'),
               (1, 's'),
               (1e-0, 's'),
               (1e-3, 'ms'),
               (1e-6, 'us'),
               (1e-9, 'ns'))


def human_f_short(number):
    if not number:
        return number
    for factor, suff in _n_suffixes:
        if number >= factor:
            break
    return "%.2f%s" % (number / factor, suff)


human_i_short = human_f_short


def human_t_short(number):
    if not number:
        return number
    for factor, suff in _t_suffixes:
        if number >= factor:
            break
    return "%.2f%s" % (number / factor, suff)


def human_i_split(number):
    num = ''
    for i, c in enumerate(str(int(number))[::-1]):
        if i % 3 == 0:
            num += ' '
        num += c
    return num[::-1].strip()
    

class Stop(Exception):
    pass
    
    
class StoppableThread(Thread):

    def __init__(self):
        super().__init__()
        self.__stop = False

    def stop(self):
        self.__stop = True

    def check_stop(self, throw=True):
        if throw and self.__stop:
            raise Stop()
        return self.__stop

    def run(self):
        try:
            self.do_run()
        except Stop:
            pass


class classinstancemethod(object):
    """ Decorator for methods that can be used both in a class or instance contex. The first argument will be either
    class or object, depending on how the method was called. """

    def __init__(self, method):
        self.method = method

    def __get__(self, obj, typ=None):
        def wrap(*args, **kwargs):
            return self.method(obj or typ, *args, **kwargs)
        return wrap


class classproperty(object):
    """ Decorator to make a method into a classproperty, read only. """

    def __init__(self, method):
        self.method = method

    def __get__(self, obj, typ):
        return self.method(typ)


