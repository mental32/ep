import sys

assert sys.version_info[:2] >= (3, 7), 'fatal: requires python3.7+'  # noqa

from .core import Bot

__author__ = 'mental'
__version__ = '1.0.0'
