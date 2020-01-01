"""Implementation of the PEP Cog."""
from contextlib import suppress
from itertools import takewhile
from typing import Dict, Optional

from aiohttp import ClientSession
from discord import Message
from ep import Cog

__all__ = {"PEP"}


@Cog.export
class PEP(Cog):
    """A cog that deals with peps."""

    BASE_URL: str = "https://www.python.org/dev/peps/pep-{ident:04}"

    def __post_init__(self):
        self._session: ClientSession = ClientSession(loop=self.loop)
        self._cache: Dict[int, str] = {}

    async def _fetch_pep(self, ident: int) -> Optional[str]:
        """Check if a pep is valid.

        Paramters
        ---------
        ident : :class:`int`
            The pep identifier, e.g. 8 or 3116

        Returns
        -------
        url : Optional[:class:`str`]
            The url of the pep, e.g. ``https://www.python.org/dev/peps/pep-0008/``
        """
        assert isinstance(ident, int)

        with suppress(KeyError):
            return self._cache[ident]

        url = self.BASE_URL.format(ident=ident)

        self.logger.info("Fetching pep %s", repr(url))
        async with self._session.get(url) as resp:
            valid = resp.status in range(200, 300)

        if valid:
            self._cache[ident] = url
            return url

        return None

    @Cog.regex(r"^(?:pep|PEP) ?(?P<span>[ \d]+)$")
    @Cog.wait_until_ready
    async def lookup(self, message: Message, *, span: str) -> None:
        """Lookup a particular PEP."""
        assert self._session is not None

        results = set(
            [
                await self._fetch_pep(ident)
                for ident in map(int, takewhile(str.isdigit, span.split(" ")))
            ]
        )

        results.discard(None)

        urls = "\n".join([f"- {result}" for result in results])
        await message.channel.send(f"{message.author.mention}:\n{urls}")
