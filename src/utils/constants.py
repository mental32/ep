import pathlib

from .helpers import codeblock

__all__ = (
	'LIB_PATH',
	'LIB_EXTS',
	'DISBOARD_BOT_PREFIX',
	'DISBOARD_BOT_ID',
	'BUMP_CHANNEL_ID',
	'TWO_HOURS',
	'PEP_URL_ERR',
	'GUILD_SNOWFLAKE',
	'WHOIS_TEMPLATE'
)

LIB_PATH = pathlib.Path(__file__).parents[0]
LIB_EXTS = _LIB_PATH.joinpath('cogs')

GUILD_SNOWFLAKE = 455072636075245588
DISBOARD_BOT_ID = 302050872383242240
BUMP_CHANNEL_ID = 575696848405397544

TWO_HOURS = (3600 * 2)

DISBOARD_BOT_PREFIX = ('!d', '!disboard')

PEP_URL_ERR = 'Invalid PEP (%s)'

WHOIS_TEMPLATE = codeblock('''
[[Member]]
username = "{member}"
ID = {member.id}

{roles}
''', style='toml')
