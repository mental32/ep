import sys

assert sys.version_info[:2] >= (3, 8), "fatal: requires python3.8+"  # noqa

from .config import *
from .utils import *
from .core import *

__author__ = "mental"
__version__ = "1.0.0"
