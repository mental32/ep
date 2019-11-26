import os
import asyncio
import sys
from functools import partial
from asyncio import run as await_
from pathlib import Path

from toml import loads as toml_loads
import click

from ep import (
    Client,
    Config,
    WebsocketServer,
    probe,
    http_probe,
    get_logger,
    infer_token,
)
from ep.tui import start as tui_start, DiscordClientConnector, WebsocketConnector

_PROBING_PREDICATE: {
    # Check if another client instance is already running locally.
    (
        lambda _, kwargs: (
            (addr := kwargs["addr"], port := kwargs["port"])
            and ({"uri": f"ws://{addr}:{port}"} if probe(addr, port) else None)
        )
    ): partial(tui_start, WebsocketConnector),

    # Check across discord if another client instance is running.
    (
        lambda config, _: (
            {"token": token}
            if await_(http_probe((token := infer_token()), config))
            else None
        )
    ): partial(tui_start, DiscordClientConnector),
}


# Process arguments
@click.command()
@click.option("-c", "--config-path", type=Path, required=True)
@click.option("-C", "--generate-config", is_flag=True)
@click.option("--probe", is_flag=True)
@click.option("--disable", is_flag=True)
@click.option("--port", type=int, default=WebsocketServer.port)
@click.option("--addr", type=str, default=WebsocketServer.host)
# Configuration overloads
@click.option("--socket-channel", type=str, default=None)
@click.option("--socket-emit", type=bool, default=None)
@click.option("--cogpath", type=Path, default=None)
def main(**kwargs):
    if kwargs["generate_config"]:
        print(Config.default)
        return

    config_path = kwargs["config_path"]
    if not config_path.exists():
        sys.exit(f"Configuration file does not exist! {config_path!r}")

    config = Config.from_file(config_path)

    # Overload the configs values with any suitable cli args.
    config_overloaders = toml_loads(Config.default)["ep"]
    for key, value in [
        (value, kwargs[value])
        for value in config_overloaders
        if kwargs.get(value, None) is not None
    ]:
        config["ep"][key] = value

    disable = kwargs["disable"]

    if not disable and kwargs["probe"]:
        addr = kwargs["addr"]
        port = kwargs["port"]

        for predicate, corofunc in _PROBING_PREDICATE.items():
            kwargs_ = predicate(config, kwargs)

            if args is not None:
                return await_(corofunc(config=config, **kwargs_))

        sys.exit("Could not find or authenticate to any local or nonlocal sessions.")

    get_logger(
        "discord", "WARN", fmt="[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s"
    )

    config["disabled"] = disable

    # We're done probing, run a client.
    with Client(config=config, disable=disable) as client:
        client.run()


if __name__ == "__main__":
    main()
