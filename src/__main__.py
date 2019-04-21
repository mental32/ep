import sys

import click

from .core import Bot

@click.command()
@click.option('--watch', default=False)
def main(watch):
    try:
        bot = Bot()
        bot.run()
    except RuntimeError as err:
        sys.exit(err)

if __name__ == '__main__':
	main()
