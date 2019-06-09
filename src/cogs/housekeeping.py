from ..utils import GuildCog


class HouseKeeping(GuildCog(455072636075245588)):
    pass


def setup(bot):
    bot.add_cog(HouseKeeping(bot))
