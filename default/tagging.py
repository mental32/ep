from asyncio import create_subprocess_shell, sleep, Future
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from typing import Type, Set, Dict, Optional
from pathlib import Path
from random import choice
from string import ascii_letters
from shutil import rmtree
from tempfile import mkdtemp
from json import loads as json_loads, dumps as json_dumps

from aiofiles import open as aiofiles_open
from discord import Message
from ep import Cog
from pydantic import BaseModel

__all__ = ("Tagging",)


class TagLookupError(LookupError):
    """Raised when no tag is found."""

async def clone_repository(repository_url: str, repository_path: str) -> Path:
    proc = await create_subprocess_shell(f"git clone {repository_url} {repository_path}", stdout=PIPE, stderr=PIPE)

    await proc.communicate()
    assert proc.returncode == 0

    return Path(repository_path)


class Tag(BaseModel):
    """Representation of a tag."""
    id: str
    body: str


@Cog.export
class Tagging(Cog):
    _base: str = r"!(t|tag)"
    _tag_id: str = r"(?P<tag_id>\d+|[A-Za-z]+)"
    _tag_body: str = r"(?P<tag_body>.{0,512})"

    _commands = Cog.group()
    _repository_path: Path

    _tails: Set[str]
    _head: Dict[str, str]

    def __post_init__(self) -> None:
        repository_url: str = self.config["default"]["tagging"]["repository"]
        repository_path: str = mkdtemp()

        task = self.client.schedule_task(clone_repository(repository_url, repository_path))

        def repository_hook_trigger(fut: Future) -> None:
            path = fut.result()
            self.logger.info("Cloned tagging repository into %s", repr(path))
            self.client.schedule_task(self._hook_repository(path))

        task.add_done_callback(repository_hook_trigger)

        self._commands.add_exception_handler(self._on_tag_exception)

    def cog_unload(self) -> None:
        if self._repository_path is None:
            return

        assert self._repository_path.exists()
        assert self._repository_path != Path(".")  # Unless you like to cry, don't remove this assertion.

        rmtree(self._repository_path)

    # Internals

    async def _hook_repository(self, path: Path) -> None:
        assert isinstance(path, Path)
        assert path.is_dir()

        self._repository_path = path

        # Index repository
        # ep.tagging/head.jsonl
        # ep.tagging/{CHANNEL_ID}.{MESSAGE_ID}

        self._tails = tails = {}
        self._head = head = {}

        if not (header := (path / "head.jsonl")).exists():
            header.touch()

        async with aiofiles_open(path / "head.jsonl") as header:
            async for entry in header:
                serialized = json_loads(entry)
                aliased = serialized["aliased"]

                async with aiofiles_open(path / aliased) as file:
                    data = json_loads(await file.read())

                tails[data["id"]] = aliased
                head[data["id"]] = aliased

                for alias in serialized["aliases"]:
                    head[alias] = aliased

    async def _write_tag(self, name: str, body: str, tag_id: Optional[str] = None) -> Tag:
        if tag_id is None:
            while (tag_id := "".join(choice(ascii_letters) for _ in range(6))) in self._tails:
                await sleep(0)

        unserialized = {"id": tag_id, "body": body}

        async with aiofiles_open(self._repository_path / name, "w") as entry:
            await entry.write(json_dumps(unserialized))

        async with aiofiles_open(self._repository_path / "head.jsonl", "a") as header:
            await header.write(json_dumps({"aliased": name, "aliases": []}) + "\n")

        self._tails[tag_id] = name
        self._head[tag_id] = name

        return Tag(**unserialized)

    async def _get_tag(self, tag_id: str) -> Tag:
        try:
            name = self._tails[tag_id]
        except KeyError:
            raise TagLookupError(f"Tag not found with id {tag_id!r}")

        async with aiofiles_open(self._repository_path / name) as entry:
            return Tag(**json_loads(await entry.read()))

    async def _on_tag_exception(self, exc, corofunc, bound) -> None:
        if isinstance(error, TagLookupError) and (message := bound.arguments.get("message", None)) is not None:
                await message.channel.send(f"{message.author.mention}, {error.args[0]!s}")

    # Public

    @Cog.regex(fr"{_base} {_tag_id}", group=_commands)
    async def get(self, message: Message, *, tag_id: str) -> None:
        """get a tag."""
        tag = await self._get_tag(tag_id)
        await message.channel.send(f"{tag.body}")

    @Cog.regex(fr"{_base} (?:a(?:lias)?) {_tag_id} (?P<alias>[A-Za-z]+)", group=_commands)
    async def alias(self, message: Message, tag_id: str, alias: str) -> None:
        """Alias a tag."""
        if alias in self._tails or alias in self._head:
            raise TagLookupError(f"That alias is already in use: {alias}")
            return

        if tag_id in self._tails:
            real = self._tails[tag_id]
        elif tag_id in self._head:
            real = self._head[tag_id]
        else:
            raise TagLookupError(f"I can't find that tag: {tag_id}")

        self._tails[alias] = real
        self._head[alias] = real

        await message.channel.send(f"{message.author.mention}, I've managed to succesfully alias {tag_id} to {alias}")

    @Cog.regex(fr"{_base} (remove|delete) {_tag_id}", group=_commands)
    async def delete(self, message: Message, *, tag_id: str) -> None:
        """Delete a tag."""

    @Cog.regex(fr"{_base} (post|create) {_tag_body}", group=_commands)
    async def post(self, message: Message, *, tag_body: str) -> None:
        """Create a tag."""
        tag = await self._write_tag(f"{message.channel.id}.{message.id}", tag_body)
        await message.channel.send(f"{message.author.mention}, I've managed to create that tag (id is `{tag.id}`)")

    @Cog.regex(fr"{_base} (put|edit) {_tag_id} {_tag_body}", group=_commands)
    async def put(self, message: Message, *, tag_id: str, tag_body: str) -> None:
        """Edit a tag"""
