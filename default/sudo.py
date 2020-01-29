from discord import Member, Message
from discord.abc import GuildChannel

from ep import Cog, ConfigValue
from ep.ext.clap import Group, Command, Argument, Option

__all__ = ("Sudo",)


@Cog.export
class Sudo(Cog):
    """A cog to perform guild maintenance."""

    __superusers = ConfigValue("ep", "superusers")
    __group = Group(prefix="!")

    @__group.check
    async def _is_sudoer(self, message: Message, command: Command):
        return message.guild is not None and message.author.id in self.__superusers

    # Guild actions.

    @Command(__group)
    @Argument("channel", type=GuildChannel)
    async def clone_channel(self, message: Message, *, channel: GuildChannel):
        """Clone a channel."""

    @Command(__group)
    @Argument("channel", type=GuildChannel)
    async def create_channel(self, message: Message, *, channel: GuildChannel):
        """Create a channel."""

    @Command(__group)
    @Argument("channel", type=GuildChannel)
    async def delete_channel(self, message: Message, *, channel: GuildChannel):
        """Delete a channel."""

    @Command(__group)
    @Argument("channel", type=GuildChannel)
    async def edit_channel(self, message: Message, *, channel: GuildChannel):
        """Edit a channel."""

    # Moderator actions.

    @Command(__group)
    @Argument("target", type=Member)
    @Option("--soft", "-s", is_flag=True)
    async def ban(self, message: Message, *, target: Member, soft: bool):
        """(soft)Ban a member."""
        fmt: str = f"Invoked by {message.author}"
        await target.ban(reason=fmt)

        if soft:
            await target.unban(reason=fmt)

    @Command(__group)
    @Argument("target", type=Member)
    async def kick(self, message: Message, *, target: Member):
        """Kick a member."""
        fmt: str = f"Invoked by {message.author}"
        await target.kick(reason=fmt)
