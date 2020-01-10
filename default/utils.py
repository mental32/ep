"""Various utilities."""
from pathlib import Path
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE

__all__ = ("clone_repository",)


async def clone_repository(repository_url: str, repository_path: str) -> Path:
    """Clone a git repsitory from a :class:`str` url into a :class:`str` path."""
    proc = await create_subprocess_shell(
        f"git clone {repository_url} {repository_path}", stdout=PIPE, stderr=PIPE
    )

    await proc.communicate()
    assert proc.returncode == 0

    return Path(repository_path)
