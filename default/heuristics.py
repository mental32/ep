"""Guild heuristics cog."""
from asyncio import gather, sleep
from collections import deque, Counter
from typing import Optional, Awaitable
from itertools import chain
from functools import lru_cache


from discord import Message, TextChannel, User, Guild
from ep import Cog, ConfigValue

__all__ = ("Heuristics",)


@Cog.export
class Heuristics(Cog):
    """Measure various heuristics."""

    guild_id: int = ConfigValue("default", "guild_snowflake")

    _messages: Optional[Counter] = None
    _socket_channel_id: Optional[int] = ConfigValue(
        "ep", "socket_channel", default=None
    )

    @property
    def guild(self) -> Guild:
        return self.client.get_guild(self.guild_id)

    @Cog.task
    @Cog.wait_until_ready
    async def _count_messages(self) -> None:
        self._messages = counter = Counter()

        guild = self.guild
        assert guild is not None

        @lru_cache(maxsize=len(guild.members))
        def skip(author: User) -> bool:
            return author.bot or author not in guild.members

        watermark: int = 200
        bucket = deque(
            [
                channel.history(limit=None, oldest_first=True)
                for channel in guild.text_channels
                if channel.id != self._socket_channel_id
            ]
        )

        while bucket:
            iterator = bucket.popleft()
            count = 0

            async for message in iterator:
                count += 1

                if count >= watermark:
                    bucket.append(iterator)
                    break

                author = message.author

                if not skip(author):
                    counter[str(author)] += 1

        self.logger.info("Completed heuristic analysis.")

    # fmt: off
    @Cog.event(tp="on_message", message_author_bot=False, message_channel_guild_id=guild_id)
    @Cog.wait_until_ready
    async def _update_counter(self, message: Message) -> None:
        self._messages[str(message.author)] += 1
    # fmt: on

    @Cog.regex(r"^!heu(?:$|(?(1)| )((?P<target>\d{17,19}))?)$")
    async def _fetch_heuristic(
        self, message: Message, *, target: Optional[int] = None
    ) -> None:

        if target is not None:
            target = self.guild.get_member(target)
        else:
            target = message.author

        amount = self._messages[str(target)]
        await message.channel.send(
            f"{message.author.mention} - `{target}` has sent `{amount!r}` messages."
        )
