import abc
import asyncio
import datetime
import time
import traceback
from abc import ABC
from dataclasses import dataclass
from collections import deque
from functools import partial
from typing import Dict, Coroutine, Union, Any, Optional, Dict, Union, List, Set

from discord import VoiceChannel
from ep.core import Cog


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

    async def action(self, cog: Cog) -> None:
        locals = {
            "guild": self.channel.guild,
            "now": datetime.datetime.now(),
        }

        await self.channel.edit(name=self.eval_template(self.template, locals=locals))


@Cog.export
class BannerCog(Cog):
    T = TypeVar("T")

    klass: T = TextBanner

    async def _alloc_banner(
        self, category_id: int, fields: List[str], bucket: Set[T]
    ) -> None:
        category = self.client.get_category(category_id)

        if category is None:
            self.logger.error("Bad category id?! %s", category_id)
            continue

        for index in range(len(fields) - len(category.voice_channels)):
            await category.create_voice_channel(name=f"Allocating banner {index}")

        for fmt, channel in zip(fields, category.voice_channels):
            bucket.add(self.klass(template=fmt, channel=channel))

    @Cog.task
    @Cog.wait_until_ready
    async def guild_banner(self) -> None:
        self.logger.info("Starting guild banner task")

        try:
            raw_banners = self.config["ep"]["banners"]
        except KeyError:
            self.logger.error("No banners were found in the config!")
            return

        entry_mapping = defaultdict(list)
        category_id: Optional[str] = None

        for entry in raw_banners:
            if entry[:11] == "category://":
                category_id = int(banner_[11:])

            entry_mapping[category_id].append(entry)

        if entry_mapping.pop(None, []):
            self.logger.warn("Found %s unreachable banner(s)!", len(banners))

        banners: Set[T] = set()
        await asyncio.gather(
            self._alloc_banner(category_id, fields, banners)
            for category_id, fields in entry_mapping.items()
        )

        bucket: Deque[Tuple[int, T]] = deque([(1, banner) for banner in banners])

        delay = 1
        while not self.client.is_closed():
            for _ in range(len(bucket)):
                interval, banner = bucket.popleft()

                if interval != 1:
                    bucket.append((interval - delay, banner))
                    continue

                task = self.client.schedule_task(banner.action(self))

                def reschedule_banner_action(_) -> None:
                    bucket.append((banner.interval, banner))

                task.add_done_callback(reschedule_banner_action)

            await asyncio.sleep(delay)
