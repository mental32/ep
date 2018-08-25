import sys

assert sys.version_info[:2] >= (3, 6), 'fatal: requires python3.6+'

import rapidjson as _json

from .core import Bot

sys.modules['json'] = _json
