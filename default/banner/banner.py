import abc
import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Union, List

from ep.core import Cog

def _eval_template(template: str, *, locals: Optional[Dict] = None) -> str:
    return eval(f'f{template!r}', None, locals)


class AbstractBannerEntry(metaclass=abc.ABCMeta):
    async def action(self, cog: Cog) -> None:
        raise NotImplementedError


@dataclass
class TextBanner(AbstractBannerEntry):
    channel_id: int
    template: str
    interval: Union[int, float] = 60.0

    _NONE_CHANNEL_ERR = "could not get channel channel_id={channel_id}"

    @property
    def _none_channel_err(self):
        return self._NONE_CHANNEL_ERR.format(channel_id=self.channel_id)

    async def action(self, cog: Cog, bucket: List[AbstractBannerEntry]) -> None:
        channel = cog.client.get_channel(self.channel_id)

        if channel is None:
            cog.logger.warn(self._none_channel_err)
            return

        locals = {
            'guild': channel.guild,
            'now': datetime.datetime.now(),
        }

        await channel.edit(name=_eval_template(self.template, locals=locals))
        bucket.append((self.interval, self))
