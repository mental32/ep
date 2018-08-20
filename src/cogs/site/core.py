import threading
import importlib
import logging
import sys
import os

import flask

from src.utils import GuildCog
from src.core import _LIB_PATH

_FLASK_BLUEPRINTS = _LIB_PATH.joinpath('cogs', 'site', 'blueprints')

def _cast_py_import_path(path):
    return str(path).replace('\\', '.').replace('/', '.')

class Site(GuildCog):
    def __init__(self, bot):
        super().__init__(bot)

        logger = logging.getLogger('werkzeug')
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.FileHandler('ep_app.log', 'a+'))

        self._app = flask.Flask(__name__)

        for file in os.listdir(f'{_FLASK_BLUEPRINTS}'):
            name = file.rsplit('.', maxsplit=1)[0]
            lib = importlib.import_module(f'{_cast_py_import_path(_FLASK_BLUEPRINTS)}.{name}')

            blueprint = getattr(lib, 'blueprint', None)

            if blueprint is None:
                del lib
                del sys.modules[name]

            self._app.register_blueprint(blueprint)

    @property
    def app(self):
        return self._app

    async def on_ready(self):
        self.bot._config['flask_args'] = ('0.0.0.0', 80)
        self.thread = t = threading.Thread(target=self.app.run, args=self.bot._config['flask_args'])
        t.daemon = True
        t.start()
