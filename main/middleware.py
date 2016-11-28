from logging import getLogger


logger = getLogger('django')


class CacheControlMiddleware(object):
    """ Middleware class that sets the CacheControl headers of a
    HTTP response to something very restrictive. """

    def process_response(self, request, response):

        if 'Cache-Control' not in response:
            response['Cache-Control'] = 'no-cache max-age=0 must-revalidate'

        return response
