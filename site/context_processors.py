from common.settings import config
from main.models import Enums


def site(request):
    """ Site context processor, to add global data to the context. """

    return {
        'enums_info': Enums.INFO_JS,
        'al': config.AL,
    }
