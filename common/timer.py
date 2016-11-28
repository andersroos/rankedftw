import time


class Timer(object):
    """ Class to measure time between points. It can be used by itself
    or using the with statement. All time is returned in seconds as a
    float.

    Usage example:

    t = Timer()
    print "Starting"
    print "First second took", t.mid(), "seconds."
    print "Second section took", t.mid(), "seconds."
    print "Total time was", t.end(), "seconds."
    """

    def __init__(self, start=True):
        """ Init the timer, if start=False it must be manually started
        with start(). """
        if start:
            self._start = time.time()
        else:
            self._start = None
        self._last = None
        self._end = None

    def start(self):
        """ Start the timer. """
        if self._start:
            raise Exception("Timer can not be started twice.")
        self._start = time.time()

    def mid(self):
        """ Take a mid timing and return it. It is either the time
        since start or the last mid timing. """

        last = self._last
        self._last = time.time()
        if last:
            return self._last - last
        else:
            return self._last - self._start

    def end(self):
        """ Ends the timer and returns time from start to end. If
        called twice it will just return the same result again. """
        if not self._end:
            self._end = time.time()
        return self._end - self._start

    def __enter__(self):
        if not self._start:
            self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.end()
    
