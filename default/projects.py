import asyncio
import sys
from urllib.parse import urlparse
from typing import List

from discord import Message, Embed

from ep import Cog

_VALID_NETLOCS: List[str] = [
    "github.com",
]


@Cog.export
class Projects(Cog):
    @Cog.event(tp="on_message", message_channel_id=633623473473847308, message_author_bot=False)
    async def parse_message(self, message: Message) -> None:
        """Handle a :class:`discord.Message` sent in the projects channel."""

        url = await self.loop.run_in_executor(None, urlparse, message.content)

        if not url.scheme:
            await message.channel.send(f"{message.author.mention} That url didn't look quite right.", delete_after=3.0)
            await asyncio.sleep(1)
            return await message.delete()

        if url.netloc not in _VALID_NETLOCS:
            await message.channel.send(f'"{message.author.mention} That doesn\'t look like a valid vcs link')
            await asyncio.sleep(1)
            return await message.delete()

        await message.channel.send(f"{message.author.mention} - <{message.content}>")
