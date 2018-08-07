import sys

if '.' not in sys.path:
    sys.path.append('.')

from src import Bot

if __name__ == '__main__':
    sys.exit(Bot.quickstart())
