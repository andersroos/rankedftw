import sys
import socket
import json

from main.models import Version, Mode


class ClientError(Exception):
    pass


class Client(object):
    """ Client for the server. :) """

    def request_server(self, data):
        try:
            raw = request_udp('localhost', 4747, json.dumps(data).encode('utf-8'))
        except socket.timeout:
            raise ClientError('Request timeout.')

        return json.loads(raw.decode('utf-8'))

    @staticmethod
    def fill_data(key=None, reverse=None, region=None, race=None, league=None):

        data = {'key': key,
                'reverse': reverse}

        if region is not None:
            data['region'] = region

        if race is not None:
            data['race'] = race

        if league is not None:
            data['league'] = league

        return data

    def get_ladder(self, key, version, mode, reverse=False, offset=None, team_id=0, limit=100,
                   region=None, race=None, league=None):

        data = self.fill_data(key, reverse, region, race, league)

        data['cmd'] = 'ladder'
        data['version'] = version
        data['mode'] = mode
        data['team_id'] = team_id
        data['limit'] = limit

        if offset is not None:
            data['offset'] = offset

        data = self.request_server(data)

        code = data.get('code', 'empty')
        if code != 'ok':
            raise ClientError("{'code': '%s', 'message': '%s'}" % (code, data.get('message', '')))
        return data

    def get_clan(self, team_ids=None, key=None, reverse=None, region=None, race=None, league=None):

        data = self.fill_data(key=key, reverse=reverse, region=region, race=race, league=league)

        data['cmd'] = 'clan'
        data['version'] = Version.LOTV
        data['mode'] = Mode.TEAM_1V1
        data['team_ids'] = team_ids

        data = self.request_server(data)

        code = data.get('code', 'empty')
        if code != 'ok':
            raise ClientError("{'code': '%s', 'message': '%s'}" % (code, data.get('message', '')))
        return data


def request_udp(host, port, message, timeout=5.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.sendto(message, (host, port))
    response = sock.recvfrom(65535)
    return response[0]


client = Client()
