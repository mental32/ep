"""Implementation of the PEP Cog."""
from contextlib import suppress
from typing import Dict

from aiohttp import ClientSession
from discord import Message
from ep import Cog

__all__ = {"PEP"}


class InvalidPEP(ValueError):
    """Raised when a pep is invalid."""


@Cog.export
class PEP(Cog):
    """A cog that deals with peps."""

    BASE_URL: str = "https://www.python.org/dev/peps/pep-{ident}"

    def __post_init__(self):
        self._session: ClientSession = ClientSession(loop=self.loop)
        self._cache: Dict[str, str] = {}

    async def _fetch_pep(self, ident: str) -> str:
        """Check if a pep is valid.

        Paramters
        ---------
        ident : :class:`str`
            The pep identifier, e.g. 8 or 3116

        Returns
        -------
        url : :class:`str`
            The url of the pep, e.g. ``https://www.python.org/dev/peps/pep-8/``

        Raises
        ------
        InvalidPEP
            Raised when the pep is invalid.
        """
        with suppress(KeyError):
            return self._cache[ident]

        url = self.BASE_URL.format(ident=ident)

        async with self._session.get(url) as resp:
            valid = resp.status in range(200, 300)

        if valid:
            self._cache[ident] = url
            return url

        raise InvalidPEP(ident)

    @Cog.regex(r"(?:pep|PEP) ?(?P<ident>\d{,12})")
    @Cog.wait_until_ready
    async def lookup(self, message: Message, *, ident: str) -> None:
        """Lookup a particular PEP."""
        assert self._session is not None

        try:
            url = await self._fetch_pep(ident)
        except InvalidPEP:
            await message.channel.send(
                f"{message.author.mention} - That's not a valid pep ({ident!r})"
            )
        else:
            await message.channel.send(f"{message.author.mention} - {url}")
