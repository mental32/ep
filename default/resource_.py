"""Cog to handle access to learning resources."""
from asyncio import Task, gather, Event, sleep
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Set, List

from discord import File
from ep import Cog, ConfigValue

from utils import clone_repository

__all__ = ("Resource",)


@Cog.export
class Resource(Cog):
    """Manage common resource access in the guild."""

    # Overloads

    _paths: List[str] = ConfigValue("default", "resource", "paths")
    _output_channel: int = ConfigValue("default", "resource", "channel_id")
    _file_limit: int = ConfigValue(
        "default", "resource", "file_limit", default=0x700000
    )

    def __post_init__(self):
        self._hook_lock = Event()
        self._temporary_paths = set()
        self._filepath_cache = {}
        self.client.schedule_task(self._hook_index_paths(self._paths))

    @Cog.destructor
    def _remove_stubs(self) -> None:
        for path in self._temporary_paths:
            rmtree(path)

    # Internal

    async def _hook(self, path: Path) -> None:
        n_large = 0
        path = path.resolve().absolute()

        def is_pdf_file(path: Path) -> bool:
            return path.is_file() and path.name.endswith(".pdf")

        for sub in filter(is_pdf_file, path.iterdir()):
            if sub.stat().st_size <= self._file_limit:
                self._filepath_cache[sub.name] = sub.resolve().absolute()
            else:
                n_large += 1

            await sleep(0)

        if n_large:
            self.logger.warn("Unable to register %s large files.", n_large)

    async def _clone_and_hook(self, url: str) -> None:
        dst = mkdtemp()
        self.logger.info(f"Cloning resource repository {url=!r} to {dst=!r}")
        path = await clone_repository(url, dst)
        self._temporary_paths.add(path)
        await self._hook(path)

    async def _hook_index_paths(self, paths: List[str]) -> None:
        tasks: Set[Task] = set()

        current_directory = Path(__file__).parent.resolve().absolute()

        for entry in paths:
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

    # Event handlers

    @Cog.event(tp="on_ready")
    async def _sync_output_channel(self) -> None:
        await self._hook_lock.wait()

        channel = self.client.get_channel(self._output_channel)

        if channel is None:
            self.logger.error("Output channel was not found.")
            return

        remotes = set()
        async for message in channel.history(limit=None):
            assert len(message.attachments) == 1
            filename = message.attachments[0].filename
            remotes.add(filename)

        cached = set(self._filepath_cache)
        for missing in cached.difference(remotes):
            self.logger.warn("Restoring missing file %s", missing)
            await channel.send(file=File(self._filepath_cache[missing]))
