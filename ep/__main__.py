import os
import asyncio
import sys
from functools import partial
from asyncio import run as await_
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from click import UsageError
from toml import loads as toml_loads

from ep import (
    Client,
    Config,
    WebsocketServer,
    probe,
    http_probe,
    get_logger,
    infer_token,
)

__all__ = ("Mutex", "main")


class Mutex(click.Option):
    def __init__(self, *args, not_required_if: List[str], **kwargs):
        self.others = others = not_required_if

        help_ = kwargs.get("help", "")
        kwargs["help"] = f"{help_} Option is mutally exclusive with {', '.join(others)}."

        super(Mutex, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        prompt, self.prompt = self.prompt, None

        if (name := self.name) in opts and any((opt := opt_) in opts for opt_ in self.others):
            self.prompt = prompt
            raise UsageError((
                f"Illegal usage: `{name}`"
                f" is mutually exclusive with {opt}."
            ))

        return super(Mutex, self).handle_parse_result(ctx, opts, args)


# Process arguments
@click.command()
@click.option("-c", "--config-path", cls=Mutex, type=Path, not_required_if=["generate_config"])
@click.option("-C", "--generate-config", is_flag=True, , not_required_if=["config_path"])
@click.option("--disable", is_flag=True)
@click.option("--ws-port", type=int, default=WebsocketServer.port)
@click.option("--ws-addr", type=str, default=WebsocketServer.host)
# Configuration overloads
@click.option("--socket-channel", type=str, default=None)
@click.option("--socket-emit", type=bool, default=None)
@click.option("--cogpath", type=Path, default=None)
def main(**kwargs):  # fmt: on
    if kwargs["generate_config"]:
        print(Config.default)
        return

    if kwargs["config_path"] is None:
        raise UsageError('Error: Missing option "-c" / "--config-path".')

    config_path = kwargs["config_path"]
    if not config_path.exists():
        sys.exit(f"Configuration file does not exist! {config_path!r}")

    config = Config.from_file(config_path)

    # Overload the configs values with any suitable cli args.
    overloads = toml_loads(Config.default)["ep"]
    for key, value in [
        (value, kwargs[value])
        for value in overloads
        if value in kwargs
    ]:
        config["ep"][key] = value


    get_logger(
        "discord", "WARN", fmt="[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s"
    )

    config["disabled"] = disable = kwargs["disable"]
    with Client(config=config, disable=disable) as client:
        client.run()


if __name__ == "__main__":
    main()
