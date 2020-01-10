"""Manage visability of projects."""
from asyncio import sleep, TimeoutError  # pylint: disable=redefined-builtin
from datetime import datetime
from functools import partial
from re import Match, search

from aiohttp import ClientSession
from discord import Message, PermissionOverwrite, TextChannel

from ep import Cog, ConfigValue


__all__ = ("Projects",)

DEALLOCATION_TIMEOUT: int = 3600  # One hour
ALLOCATED_MESSAGE: str = (
    "{message.author.mention} - Here's the webhook url: {webhook.url}\nbe sure"
    " to push an event within the hour otherwise I'm removing this channel."
)


@Cog.export
class Projects(Cog):
    """Cog that reacts appropriately to project urls."""

    _index_channel: int = ConfigValue("default", "projects", "index_channel_id")

    _default_kwargs = {
        "pattern": r"^(?:webhook!)?https?://($hosts)(?:.{0,200})$$",
        "message_channel_id": _index_channel,
        "message_author_bot": False,
        "formatter": lambda client: {
            "hosts": "|".join(client.config["default"]["projects"]["hosts"])
        },
    }

    _negative_lookahed = {
        **_default_kwargs,
        "filter_": (lambda match: isinstance(match, Match)),
    }

    _category_id: int = ConfigValue("default", "projects", "category_id")
    _member_role_id: int = ConfigValue("default", "guild_member_role")

    session: ClientSession

    def __post_init__(self):
        self.session = ClientSession()

    # Internal

    async def _activate_webhook_channel(
        self, channel: TextChannel, timeout: int = DEALLOCATION_TIMEOUT
    ) -> None:
        def is_webhook_message(message: Message) -> bool:
            return message.channel == channel and message.webhook_id is not None

        wait_for = partial(self.client.wait_for, "message")

        try:
            await wait_for(check=is_webhook_message, timeout=timeout)
        except TimeoutError:
            await channel.delete()
            return

        self.logger.info("Activating webhook channel %s", repr(channel))

        def is_not_webhook(message: Message) -> bool:
            return message.webhook_id is None

        await channel.purge(limit=None, check=is_not_webhook, bulk=True)
        await channel.edit(sync_permissions=True)

    # Zombie rescheduler

    @Cog.task
    @Cog.wait_until_ready
    async def _reschedule_orphan_channels(self) -> None:
        category = self.client.get_channel(self._category_id)
        assert category is not None

        schedule_task = self.client.schedule_task
        for channel in category.channels:
            if channel.id == self._index_channel:
                continue

            timeout = None
            now = datetime.now()

            async for message in channel.history(limit=None, oldest_first=True):
                if message.webhook_id is not None:
                    timeout = None
                    break

                if timeout is None:
                    timeout = DEALLOCATION_TIMEOUT - (now - message.created_at).seconds

                    if timeout <= 0:
                        timeout = DEALLOCATION_TIMEOUT

            if timeout is not None:
                self.logger.warn(
                    "Rescheduling activation task for channel timeout=%s channel=%s",
                    timeout,
                    repr(channel),
                )
                schedule_task(self._activate_webhook_channel(channel, timeout))

    # Listeners

    @Cog.formatted_regex(**_negative_lookahed)
    async def filter_project_message(self, message: Message) -> None:
        """Handle a :class:`discord.Message` sent in the projects channel."""
        await message.channel.send(
            f"{message.author.mention}, That doesn't look like a valid vcs link.",
            delete_after=3.0,
        )
        await sleep(0.5)
        await message.delete()

    @Cog.formatted_regex(**_default_kwargs)
    @Cog.wait_until_ready
    async def webhook_project_repository(self, message: Message) -> None:
        """Generate a channel and webhook for a repository."""
        assert message.content.startswith("webhook!")

        url = message.content[len("webhook!") :]

        async with self.session.get(url) as resp:
            if not resp.status in range(200, 300):
                await message.channel.send(f"{message.author.mention} - I couldn't verify that link, I got a HTTP/{resp.status} back.", delete_after=3.0)
                await sleep(2)
                await message.delete()
                return

        kwargs = {"topic": url, "reason": f"Invoked by {message.author!s}"}

        match = await self.client.loop.run_in_executor(
            None, partial(search, r"([^/][\w-]+)(?:/)([^/].+)$", url)
        )

        if match is not None:
            name = "-".join(match.groups())
        else:
            self.logger.error("Failed to match against %s", repr(url))
            name = url

        if len(name) > 80:
            name = name[:80]

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
                read_messages=True, read_message_history=True, send_messages=True
            ),
        }

        channel = await category.create_text_channel(**kwargs)
        webhook = await channel.create_webhook(name=name)

        await channel.send(ALLOCATED_MESSAGE.format(message=message, webhook=webhook))
        self.client.schedule_task(self._activate_webhook_channel(channel))
