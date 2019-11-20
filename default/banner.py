import abc
import asyncio
import datetime
import time
import traceback
from abc import ABC
from dataclasses import dataclass
from collections import deque
from functools import partial
from typing import Dict, Coroutine, Union, Any, Optional, Dict, Union, List

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
    channel_id: int
    template: str
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

        # repr(str) produces quotes around the output
        # prefix an `f` and you'll end up with perfectly
        # legal f-string syntax ready for immediate evalutaion
        return eval(f'f{template!r}', None, locals)

    async def action(self, cog: Cog) -> None:
        channel = cog.client.get_channel(self.channel_id)

        if channel is None:
            err = self._NONE_CHANNEL_ERR.format(channel_id=self.channel_id)
            cog.logger.warn(err)
            return

        locals = {
            'guild': channel.guild,
            'now': datetime.datetime.now(),
        }

        await channel.edit(name=self.eval_template(self.template, locals=locals))


@Cog.export
class BannerCog(Cog):

    klass = TextBanner

    @Cog.task
    @Cog.wait_until_ready
    async def guild_banner(self) -> None:
        self.logger.info("Starting guild banner task")

        try:
            raw_banners = self.config["ep"]["banners"]
        except KeyError:
            self.logger.error("No banners were found in the config!")
            return

        banners = [self.klass(**entry.copy()) for entry in raw_banners]
        bucket = deque([(1, banner) for banner in banners])

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
