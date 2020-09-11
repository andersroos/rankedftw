import logging
import threading


threadlocal = threading.local()
region_names = {0: 'eu',
                1: 'am',
                2: 'kr',
                3: 'sea',
                4: 'cn'}


def log_feature(feature):
    threadlocal.feature = feature[:6]


def log_region(region):
    threadlocal.region = region[:3].upper()
    
    
def threadlocal_region():
    return getattr(threadlocal, 'region', 'UNK')


def threadlocal_feature():
    return getattr(threadlocal, 'feature', '')


class LogContext(object):

    def __init__(self, region=None, feature=None):
        self.region = region
        self.feature = feature
        self.o_region = None
        self.o_feature = None
        
    def __enter__(self):
        if self.region is not None:
            self.o_region = threadlocal_region()
            if isinstance(self.region, int):
                region = region_names[self.region]
            else:
                region = self.region
            log_region(region)
            
        if self.feature is not None:
            self.o_feature = threadlocal_feature()
            log_feature(self.feature)
    
    def __exit__(self, type, value, traceback):
        if self.o_region is not None: log_region(self.o_region)
        if self.o_feature is not None: log_feature(self.o_feature)


def log_context(feature=None, region=None):
    def dec(func):
        def wrapper(*args, **kwargs):
            nonlocal region
            nonlocal feature
            r = region
            f = feature
            if r is None:
                r = kwargs.get('region', None)
            if r is None and args:
                r = getattr(args[0], 'region', None)
            with LogContext(region=r, feature=f):
                return func(*args, **kwargs)
        return wrapper
    return dec


class Formatter(logging.Formatter):

    f0 = "{r.asctime} {r.levelname: <7}"
    f1 = "[{r.process: >5}/{r.threadName: <10} {r.pathname: >24}:{r.lineno}]"
    f2 = "{r.feature} {r.region: >3}:"

    f = "{0} {1: <48} {2: >11} {3}"
        
    def __init__(self, *args, **kwargs):
        super().__init__(fmt="%(asctime)s %(levelname)s [%(process)d/%(threadName)s "
                             "%(pathname)s:%(lineno)d]: %(message)s")
    
    def format(self, record):
        if hasattr(record, 'cpp_line'):
            record.lineno = record.cpp_line
            delattr(record, 'cpp_line')
            
        if hasattr(record, 'cpp_file'):
            record.pathname = record.cpp_file
            delattr(record, 'cpp_file')
        
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        record.threadName = record.threadName[-10:]
        record.pathname = record.pathname[-24:]
        record.region = threadlocal_region()
        record.feature = threadlocal_feature()
        s0 = self.f0.format(r=record)
        s1 = self.f1.format(r=record)
        s2 = self.f2.format(r=record)
        s = self.f.format(s0, s1, s2, record.message)
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s


def formatterFactory(*args, **kwargs):
    return Formatter()
    
