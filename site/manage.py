#!/usr/bin/env python3
import sys

from rocky import syspath
from django.conf import settings
from django.core.management import execute_from_command_line


if __name__ == "__main__":

    syspath.add('..', __file__)

    from common.settings import site_settings

    settings.configure(**site_settings())
    execute_from_command_line(sys.argv)
