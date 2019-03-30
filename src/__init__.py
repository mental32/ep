import sys

assert sys.version_info[:2] >= (3, 6), 'fatal: requires python3.6+'

from .core import Bot

__version__ = '1.0.0'
