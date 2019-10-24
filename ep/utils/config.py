from pathlib import Path
from typing import Dict, Union

import toml

class Config:
    @classmethod
    def from_file(self, file: Union[Path, str]) -> "Config":
        """Read the configuration at a filepath and return a dict.

        Parameters
        ----------
        file : :class:`Path`
            The file to read.
        """
        assert file.exists(), "This file does not appear to exist!"

        with open(file.absolute().resolve(), "r") as inf:
            return toml.loads(inf.read())
