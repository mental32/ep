"""Manage visability of projects."""
from asyncio import sleep, TimeoutError  # pylint: disable=redefined-builtin
from re import Match, search
from functools import partial

from discord import Message, PermissionOverwrite, TextChannel

from ep import Cog


__all__ = ("Projects",)

DEALLOCATION_TIMEOUT: int = 3600  # One hour
ALLOCATED_MESSAGE: str = (
    "{message.author.mention} - Here's the webhook url: {webhook.url}\nbe sure"
    " to push an event within the hour otherwise I'm removing this channel."
)


@Cog.export
class Projects(Cog):
    """Cog that reacts appropriately to project urls."""

    _url_re: str = r"https?://($hosts)(?:.{0,200})$$"

    _default_kwargs = {
        "message_channel_id": 633623473473847308,
        "message_author_bot": False,
        "formatter": lambda client: {
            "hosts": "|".join(client.config["default"]["projects"]["hosts"])
        },
    }

    _negative_lookahed = {
        **_default_kwargs,
        "filter_": (lambda match: isinstance(match, Match)),
    }

    def __post_init__(self):
        self._category_id = self.config["default"]["projects"]["category_id"]
        self._member_role_id = self.config["default"]["guild_member_role"]

    # Internal

    async def _activate_webhook_channel(self, channel: TextChannel) -> None:
        def is_webhook_message(message: Message) -> bool:
            return message.channel == channel and message.webhook_id is not None

        wait_for = partial(self.client.wait_for, "message")

        try:
            await wait_for(check=is_webhook_message, timeout=DEALLOCATION_TIMEOUT)
        except TimeoutError:
            await channel.delete()
            return

        self.logger.info("Activating webhook channel %s", repr(channel))

        async for message in channel.history(limit=None):
            if message.webhook_id is not None:
                await message.delete()

        await channel.edit(sync_permissions=True)

    # Listeners

    @Cog.formatted_regex(pattern=fr"^(?<!webhook!){_url_re}", **_negative_lookahed)
    async def filter_project_message(self, message: Message) -> None:
        """Handle a :class:`discord.Message` sent in the projects channel."""
        await message.channel.send(
            f"{message.author.mention}, That doesn't look like a valid vcs link.",
            delete_after=3.0,
        )
        await sleep(0.5)
        await message.delete()

    @Cog.formatted_regex(pattern=fr"^(?:webhook!){_url_re}", **_default_kwargs)
    @Cog.wait_until_ready
    async def webhook_project_repository(self, message: Message) -> None:
        """Generate a channel and webhook for a repository."""
        assert message.content.startswith("webhook!")

        url = message.content[len("webhook!") :]

        kwargs = {"topic": url, "reason": f"Invoked by {message.author!s}"}

        match = await self.client.loop.run_in_executor(
            None, partial(search, r"([^/]\w+)(?:/)([^/]\w+)$", url)
        )

        if match is not None:
            name = "-".join(match.groups())
        else:
            name = url

        assert len(name) <= 80

        kwargs["name"] = name

        category = self.client.get_channel(self._category_id)
        assert category is not None

        member_role = message.guild.get_role(self._member_role_id)
        assert member_role is not None

        kwargs["overwrites"] = {
            **category.overwrites,
            member_role: PermissionOverwrite(
                read_messages=False, read_message_history=False
            ),
            message.author: PermissionOverwrite(
                read_messages=True, read_message_history=True
            ),
        }

        channel = await category.create_text_channel(**kwargs)
        webhook = await channel.create_webhook(name=name)

        await channel.send(ALLOCATED_MESSAGE.format(message=message, webhook=webhook))
        self.client.schedule_task(self._activate_webhook_channel(channel))
