import sys

if '.' not in sys.path:
    sys.path.append('.')

from src import Bot

if __name__ == '__main__':
	try:
		Bot()
	except RuntimeError as err:
		sys.exit(err)
