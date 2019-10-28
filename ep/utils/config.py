import pathlib
from typing import Dict, Union, Any

import toml

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
""".strip()


class Config:
    """A class that deals with configuration issues.

    Attributes
    ----------
    default : :class:`str`
        The default toml configuration.
    """
    default: str = _DEFAULT

    def __init__(self, data: Dict, fp: pathlib.Path) -> None:
        self.fp = fp
        self.data = data

    def __getitem__(self, key: Any) -> Any:
        return self.data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.data[key] = value

    # Constructors

    @classmethod
    def from_file(cls, file: Union[pathlib.Path, str]) -> "Config":
        """Read the configuration at a filepath and return a dict.

        Parameters
        ----------
        file : Union[:class:`pathlib.Path`, :class:`str`]
            The file to read.
        """
        if isinstance(file, str):
            path = pathlib.Path(file)
        elif isinstance(file, pathlib.Path):
            path = file
        else:
            raise TypeError()

        path = path.resolve().absolute()

        with open(path) as inf:
            return cls(toml.loads(inf.read()), fp=path)
