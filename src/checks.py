from discord.ext import commands

def is_db_ready():
	def _check_db(ctx):
		return hasattr(ctx.bot, '_database') and ctx.bot._database.is_ready()
	return commands.check(_check_db)
