import sys

from argparse import ArgumentTypeError, ArgumentParser
from contextlib import ExitStack
from logging import getLogger
from rocky.process import stoppable
from common.settings import config
from main.models import Region
from rocky.argparse import log_args
from rocky.pid_file import pid_file
from rocky.process import log_exception


class Command(object):

    def __init__(self, description, pid_file=True, stoppable=True, pid_file_max_age=86400, *args, **kwargs):
        self.parser = ArgumentParser(description=description)
        self._pid_file = pid_file
        self._pid_file_max_age = pid_file_max_age
        self._stoppable = stoppable
        self._stoppable_instance = None

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    def __call__(self):
        status = 1
        with log_exception(status=1):
            args = self.parser.parse_args()
            log_args(args)
            config.log_cached()
            logger = getLogger('django')

            with ExitStack() as stack:
                if self._pid_file:
                    stack.enter_context(pid_file(dirname=config.PID_DIR, max_age=self._pid_file_max_age))

                if self._stoppable:
                    self._stoppable_instance = stoppable()
                    stack.enter_context(self._stoppable_instance)

                status = self.run(args, logger) or 0
        sys.exit(status)

    def check_stop(self, throw=True):
        if self._stoppable_instance:
            return self._stoppable_instance.check_stop(throw=throw)
        return True

    def run(self, args, logger):
        return 1


def regions(arg):
    """ Argpase Argument that is a comma separeted list of region keys, arg will store ids. """
    try:
        return sorted([Region.id_by_keys[k] for k in arg.split(',')])
    except KeyError as e:
        raise ArgumentTypeError("Not a valid region: %s" % str(e))


class RegionsArgMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('--regions', '-r', dest="regions", default='eu,am,kr,cn,sea', type=regions,
                                 help="The regions (comma separated) to use.")
