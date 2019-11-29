from asyncio import sleep
from re import Match
from typing import List, Dict, Any

from discord import Message, Embed

from ep import Cog


def _resolve_hosts(client) -> Dict[str, Any]:
    return {"hosts": "|".join(client.config["default"].get("valid_vcs", []))}


@Cog.export
class Projects(Cog):
    _default_kwargs = {
        "formatter": _resolve_hosts,
        "filter_": (lambda match: isinstance(match, Match)),
        "pattern": r"https?://($hosts)(?:.{0,200})",
        "message_channel_id": 633623473473847308,
        "message_author_bot": False,
    }

    @Cog.formatted_regex(**_default_kwargs)
    async def filter_project_message(self, message: Message) -> None:
        """Handle a :class:`discord.Message` sent in the projects channel."""
        await message.channel.send(
            f"{message.author.mention}, That doesn't look like a valid vcs link.",
            delete_after=3.0,
        )
        await sleep(1.5)
        await message.delete()
