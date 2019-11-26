import pathlib
from typing import Dict, Union, Any

from toml import loads as toml_loads

_DEFAULT: str = """
[ep]
# When a "cogpath" is specified ep will attempt to import python modules
# in the directory specified by the "cogpath" variable.
#
# cogpath = "."  # relative to the current file

# "socket_channel" is the discord channel id of the channel to use for
# network agnostic communication, used with the tui control panel.
#
# socket_channel = 1234567890

# "superusers" is a list of discord user snowflakes and its used to auth
# users when the TUI connects through discord directly.
# 
# superusers = []
""".strip()


class Config:
    """A class that deals with configuration issues.

    Attributes
    ----------
    default : :class:`str`
        The default toml configuration.
    """

    default: str = _DEFAULT

    def __init__(self, data: Dict, fp: Path) -> None:
        self.fp = fp
        self.data = data

    def __getitem__(self, key: Any) -> Any:
        return self.data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.data[key] = value

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
