import sys

assert sys.version_info[:2] >= (3, 7), "fatal: requires python3.7+"  # noqa

from . import utils
from .utils import probe
from .core import Client
from . import tui

__author__ = "mental"
__version__ = "1.0.0"
