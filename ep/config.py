from pathlib import Path
from typing import Dict, Union, Any

from toml import loads as toml_loads

_DEFAULT: str = """
[ep]
# When a "cogpath" is specified ep will attempt to import python modules
# in the directory specified by the "cogpath" variable.
#
cogpath = "."  # relative to the current file

# "socket_channel" is the discord channel id of the channel to use for
# network agnostic communication, used with the tui control panel.
#
socket_channel = 1234567890

# "socket_emit" is used to control whether to relay socket messages into
# the "socket_channel"
socket_emit = true

# "superusers" is a list of discord user snowflakes and its used to auth
# users when the TUI connects through discord directly.
# 
superusers = []
""".strip()


class Config(dict):
    """A class that deals with configuration issues.

    Attributes
    ----------
    default : :class:`str`
        The default toml configuration.
    """

    default: str = _DEFAULT

    def __init__(self, *args, fp: Path, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fp = fp

    # Constructors

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "Config":
        """Read the configuration at a filepath and return a dict.

        >>> config = Config.from_file("./ep.toml")

        Parameters
        ----------
        file : Union[:class:`pathlib.Path`, :class:`str`]
            The file to read.
        """
        if isinstance(file, str):
            path = Path(file)
        elif isinstance(file, Path):
            path = file
        else:
            raise TypeError(
                "`file` argument must be a string or pathlib.Path instance."
            )

        path = path.resolve().absolute()

        return cls(toml_loads(path.read_text()), fp=path)
