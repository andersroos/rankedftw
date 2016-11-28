from functools import wraps
from django.conf import settings
from django.core.cache import cache


def caching(func):
    """ Method decorator to cache the return value on the
    object/class. Use on methods with arguments is not allowed. """

    def wrapper(self):
        prop = func.__name__ + '__result_cache__'
        if hasattr(self, prop):
            return getattr(self, prop)
        result = func(self)
        setattr(self, prop, result)
        return result
    
    return wrapper


def cache_control(cache_control):
    """ Decorator to set Cache-Control http header. """

    def decorator(view):
        @wraps(view)
        def wrap(*args, **kwargs):
            response = view(*args, **kwargs)
            if not settings.DEBUG:
                response['Cache-Control'] = cache_control
            return response
        return wrap
    return decorator


def cache_value(key, timeout, value_creator, *args, **kwargs):
    """ Returns value if cache, othevise use value_creator with args and
    kwargs callable to create a new value. """
    
    value = cache.get(key)
    if value is not None:
        return value

    value = value_creator(*args, **kwargs)
    cache.set(key, value, timeout)
    return value
    
