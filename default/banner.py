from asyncio import Future, gather, sleep
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque, defaultdict
from functools import partial
from typing import (
    Dict,
    Coroutine,
    Union,
    Any,
    Optional,
    Dict,
    Union,
    List,
    Set,
    TypeVar,
)

from discord import VoiceChannel
from ep.core import Cog

_STALLING: str = "Stalling for 60 seconds, websocket seems to be closed."


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

    _NONE_CHANNEL_ERR = "could not get channel channel_id={channel_id}"

    def __hash__(self):
        return hash(self.channel)

    @staticmethod
    def eval_template(template: str, *, locals: Optional[Dict] = None) -> str:
        """Evaluate a template for a given set of locals.

        Parameters
        ----------
        template : :class:`str`
            The template to evaluate.
        locals : Optional[:class:`collections.abc.Mapping`]
            The locals to use, None of none provided.
        """
        assert isinstance(template, str)

        if locals is None:
            locals = {}

        # repr(str) produces quotes around the output
        # prefix an `f` and you'll end up with perfectly
        # legal f-string syntax ready for immediate evalutaion
        return eval(f"f{template!r}", {}, locals)

    async def action(self, cog: Cog) -> "Banner":
        locals = {
            "guild": self.channel.guild,
            "now": datetime.now(),
        }

        await self.channel.edit(name=self.eval_template(self.template, locals=locals))
        return self


@Cog.export
class BannerCog(Cog):
    T = TypeVar("T")

    klass: T = TextBanner

    async def _alloc_banner_slots(
        self, category_id: int, fields: List[str], bucket: Set[T]
    ) -> None:
        category = self.client.get_channel(category_id)

        if category is None:
            self.logger.error("Bad category id?! %s", category_id)
            return

        for index in range(len(fields) - len(category.voice_channels)):
            await category.create_voice_channel(name=f"Allocating banner {index}")

        for fmt, channel in zip(fields, category.voice_channels):
            bucket.add(self.klass(template=fmt, channel=channel))

    @Cog.task
    @Cog.wait_until_ready
    async def guild_banner(self) -> None:
        self.logger.info("Starting guild banner task")

        try:
            raw_banners = self.config["default"]["banners"]
        except KeyError:
            self.logger.error("No banners were found in the config!")
            return

        entry_mapping = defaultdict(list)
        category_id: Optional[str] = None

        for entry in raw_banners:
            if entry[:11] == "category://":
                category_id = int(entry[11:])
            else:
                entry_mapping[category_id].append(entry)

        if entry_mapping.pop(None, []):
            self.logger.warn("Found %s unreachable banner(s)!", len(banners))

        banners: Set[T] = set()
        coros = [self._alloc_banner_slots(*args, banners) for args in entry_mapping.items()]
        await gather(*coros)

        bucket: Set[Tuple[int, T]] = {(1, banner) for banner in banners}

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
