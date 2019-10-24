import asyncio
import datetime
import time
import traceback
from collections import deque
from typing import Dict, Coroutine, Union, Any

from ep.core import Cog

from .banner import AbstractBannerEntry, TextBanner

BANNERS = {"text": TextBanner}


@Cog.export
class BannerCog(Cog):
    @staticmethod
    def _new_banner(entry: Dict) -> AbstractBannerEntry:
        _type = entry.pop("type", "text")
        kwargs = {key.lower(): data for key, data in entry.items()}
        return BANNERS[_type](**kwargs)

    @Cog.task
    async def guild_banner(self) -> None:
        await self.client.wait_until_ready()
        self.logger.info("Starting guild banner task")

        try:
            raw_banners = self.config["ep"]["banners"]
        except KeyError:
            self.logger.error("No banners were found in the config!")
            return

        banners = [self._new_banner(entry.copy()) for entry in raw_banners]
        bucket = deque([(1, banner) for banner in banners])

        while not self.client.is_closed():
            delay = 0.25

            for _ in range(len(bucket)):
                interval, banner = bucket.popleft()

                if interval != 1:
                    bucket.appendleft((interval - 1, banner))
                    continue

                self.client.schedule_task(banner.action(self, bucket))
            else:
                delay = 1

            await asyncio.sleep(delay)
