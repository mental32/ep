"""Cog to handle access to learning resources."""
from asyncio import Task, gather, Event, sleep
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Set

from discord import Message, File, HTTPException
from ep import Cog

from tagging import clone_repository

__all__ = ("Resource",)


@Cog.export
class Resource(Cog):
    """Manage common resource access in the guild."""

    def __post_init__(self):
        self._hook_lock = Event()
        self._paths = self.config["default"]["resource"]["paths"]
        self._output_channel = self.config["default"]["resource"]["channel_id"]
        self.client.schedule_task(self._hook_index_paths())
        self._temporary_paths = set()
        self._filepath_cache = {}

    def cog_unload(self) -> None:
        for path in self._temporary_paths:
            rmtree(path)

    async def _hook(self, path: Path) -> None:
        for sub in path.iterdir():
            if sub.is_file() and sub.name.endswith(".pdf"):
                self._filepath_cache[sub.name] = sub
            await sleep(0)

    async def _clone_and_hook(self, url: str) -> None:
        dst = mkdtemp()
        self.logger.info(f"Cloning resource repository {url=!r} to {dst=!r}")
        path = await clone_repository(url, dst)
        self._temporary_paths.add(path)
        await self._hook(path)

    async def _hook_index_paths(self) -> None:
        tasks: Set[Task] = set()

        current_directory = Path(__file__).parent.resolve().absolute()

        for entry in self._paths:
            if any(
                entry.startswith(protocol)
                for protocol in ("http://", "https://", "git://")
            ):
                coro = self._clone_and_hook(entry)
            elif (path := (current_directory / Path(entry))).exists():
                coro = self._hook(path)
            else:
                self.logger.error(
                    "Bad entry in resource paths %s (%s)", repr(entry), repr(path)
                )
                continue

            tasks.add(self.client.schedule_task(coro))

        await gather(*tasks)
        self._hook_lock.set()

    @Cog.event(tp="on_ready")
    async def _sync_output_channel(self) -> None:
        await self._hook_lock.wait()

        channel = self.client.get_channel(self._output_channel)

        if channel is None:
            self.logger.error("Output channel was not found.")
            return

        def has_file_attachment(message: Message) -> bool:
            return message.attachments

        def into_filename(message: Message) -> str:
            return message.attachments[0].filename

        cached_filenames = set(self._filepath_cache)
        remote_filenames = {
            filename
            async for filename in channel.history(limit=None)
            .filter(has_file_attachment)
            .map(into_filename)
        }

        difference = cached_filenames.difference(remote_filenames)
        self.logger.info("Attempting to sync %s file(s)", len(difference))

        for filename in difference:
            path = self._filepath_cache[filename]

            self.logger.info("Attempting to sync file %s", repr(path))
            try:
                await channel.send(file=File(path))
            except HTTPException as err:
                self.logger.error("Could not sync file: %s (%s)", repr(filename), err)

        self.logger.info("Done syncing file contents.")
