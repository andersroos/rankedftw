#!/usr/bin/env python3

import os

# noinspection PyUnresolvedReferences
import init_django

from requests import request
from requests.auth import HTTPBasicAuth

from common.settings import config
from tasks.base import Command


#
# Tokens from client credentials request seems to work on all regions so region is not really needed.
#
# US EU KR TW
# https://<region>.battle.net/oauth/authorize
# https://<region>.battle.net/oauth/token
#
# CN
# https://www.battlenet.com.cn/oauth/authorize
# https://www.battlenet.com.cn/oauth/token
#
# See also http://us.battle.net/forums/en/bnet/topic/20749867301
#


class Main(Command):

    def __init__(self):
        super().__init__("Fetch a new access token and store it in the config file.", stoppable=False)

        self.add_argument('--filename', '-f', dest="filename",
                          default=os.path.join(config.CONF_DIR, 'access_token'),
                          help="File to save access token in.")

    def run(self, args, logger):
        url = 'https://eu.battle.net/oauth/token'
        logger.info(f"requesting token from {url}")
        response = request('POST',
                           url,
                           auth=HTTPBasicAuth(config.API_KEY, config.API_SECRET),
                           params=dict(grant_type='client_credentials'),
                           allow_redirects=False)

        if response.status_code != 200:
            logger.error("failed to get access token got %s: %s" % (response.status_code, response.content))
            return 1

        data = response.json()
        access_token = data['access_token']
        logger.info("writing access_token to %s, expires in %s" % (args.filename, data['expires_in']))
        with open(args.filename, 'w') as f:
            f.write(access_token)
        return 0


if __name__ == '__main__':
    Main()()
