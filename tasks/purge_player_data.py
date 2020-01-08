# noinspection PyUnresolvedReferences
import init_django

from main.purge import purge_player_data
from tasks.base import Command
from common.logging import log_region


class Main(Command):

    def __init__(self):
        super().__init__("Purge player data that is no longer available in the API from the db.",
                         pid_file=True, stoppable=True)

    def run(self, args, logger):
        log_region('ALL')
        purge_player_data(check_stop=self.check_stop)
        return 0


if __name__ == '__main__':
    Main()()
