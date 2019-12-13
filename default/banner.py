"""Use VoiceChannel's grouped by Categories as output for some configuration."""

from asyncio import Future, gather, sleep
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from itertools import chain, starmap, cycle
from typing import Tuple, Dict, Union, Optional, List, Set, TypeVar, DefaultDict

from discord import VoiceChannel
from ep.core import Cog

__all__ = ("BannerCog",)

_STALLING: str = "Stalling for 60 seconds, websocket seems to be closed."

T = TypeVar("T")  # pylint: disable=invalid-name


@dataclass
class TextBanner:
    """A banner that has only a textual element.

    Attributes
    ----------
    channel_id : :class:`int`
        The target channel id
    template : :class:`str`
        The template used.
    interval : Union[:class:`int`, :class:`str`]
        The interval of delay between actions.
    """

    template: str
    channel: VoiceChannel
    interval: Union[int, float] = 60.0

    _previous: Optional[str] = field(init=False, default=None)

    def __hash__(self):
        return hash(self.channel)

    @staticmethod
    def eval_template(template: str, *, locals_: Optional[Dict] = None) -> str:
        """Evaluate a template for a given set of locals_.

        Parameters
        ----------
        template : :class:`str`
            The template to evaluate.
        locals_ : Optional[:class:`collections.abc.Mapping`]
            The locals to use, None of none provided.
        """
        assert isinstance(template, str)

        if locals_ is None:
            locals_ = {}

        # repr(str) produces quotes around the output
        # prefix an `f` and you'll end up with perfectly
        # legal f-string syntax ready for immediate evalutaion
        return eval(f"f{template!r}", {}, locals_)  # pylint: disable=eval-used

    async def action(self, cog: Cog) -> "Banner":
        """Edit the surrogate channels name with the evaluated template."""
        locals_ = {
            "cog": cog,
            "guild": self.channel.guild,
            "now": datetime.now(),
        }

        evaluated = self.eval_template(self.template, locals_=locals_)

        if evaluated != self._previous:
            await self.channel.edit(name=evaluated)

        self._previous = evaluated

        return self


@Cog.export
class BannerCog(Cog):
    """Handle a guilds banner channels."""
    klass: T = TextBanner

    graph: DefaultDict[int, List[str]]

    def __post_init__(self):
        raw: List[str] = self.config["default"]["banner"].get("entries", [])

        entry_mapping: DefaultDict[int, List[str]] = defaultdict(list)
        category_id: int = 0

        for entry in raw:
            if entry[:11] == "category://":
                category_id = int(entry[11:])
            else:
                entry_mapping[category_id].append(entry)

        if garbage := entry_mapping.pop(0, []):
            self.logger.warn("Found %s unreachable banner(s)!", len(garbage))

        self.graph = entry_mapping

    async def _alloc_banner_slots(self, category_id: int, fields: List[str]) -> Set[T]:
        category = self.client.get_channel(category_id)

        if category is None:
            self.logger.error("Bad category id?! %s", category_id)
            return

        for index in range(len(fields) - len(category.voice_channels)):
            self.logger.info("%s - Allocating banner %s", category_id, index)
            await category.create_voice_channel(name=f"Allocating banner {index}")

        return {
            self.klass(template=fmt, channel=channel)
            for fmt, channel in zip(fields, category.voice_channels)
        }

    @Cog.task
    @Cog.wait_until_ready
    async def _guild_banner_task(self) -> None:
        self.logger.info("Starting guild banner task")

        gathered = await gather(*starmap(self._alloc_banner_slots, self.graph.items()))

        bucket: Set[Tuple[int, T]] = set(zip(cycle([1]), chain.from_iterable(gathered)))

        del gathered

        delay = 1
        while True:
            if self.client.is_closed():
                await sleep(60)
                self.logger.warn(_STALLING)
                continue

            for _ in range(len(bucket)):
                interval, banner = bucket.pop()

                if (delta := (interval - delay)) > 0:
                    bucket.add((delta, banner))
                    continue

                task = self.client.schedule_task(banner.action(cog=self))

                def reschedule_banner_action(fut: Future) -> None:
                    banner = fut.result()
                    assert isinstance(banner, TextBanner), (banner, fut)
                    bucket.add((banner.interval, banner))

                task.add_done_callback(reschedule_banner_action)

            await sleep(delay)

        self.logger.info("Banner task stopped")
