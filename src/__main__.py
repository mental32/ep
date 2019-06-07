import sys

from .core import Bot

if __name__ == '__main__':
    try:
        Bot().run()
    except RuntimeError as err:
        sys.exit(err)
