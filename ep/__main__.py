import os
import asyncio
import sys
import pathlib

import click

from ep import Client, Config, WebsocketServer, probe, http_probe, tui, get_logger
from ep.tui import DiscordClientConnector, WebsocketConnector


@click.command()
@click.option("-c", "--config", type=pathlib.Path)
@click.option("-C", "--generate-config", is_flag=True)
@click.option("--probe", is_flag=True)
@click.option("--disable", is_flag=True)
@click.option("--port", type=int, default=WebsocketServer.port)
@click.option("--addr", type=str, default=WebsocketServer.host)
def main(**kwargs):
    if kwargs["generate_config"]:
        print(Config.default)
        return

    disable = kwargs["disable"]
    addr = kwargs["addr"]
    port = kwargs["port"]

    should_probe = kwargs["probe"]

    if not disable and should_probe and probe(addr, port):
        # There is another client running and bound to this port.
        uri = f"ws://{addr}:{port}"
        asyncio.run(tui.start(WebsocketConnector, uri=uri))
        return

    config = kwargs["config"]

    if config is None:
        sys.exit("Please supply a configuration file.")

    config = Config.from_file(config)

    if not disable and should_probe:
        try:
            token = os.environ["DISCORD_TOKEN"]
        except KeyError:
            sys.exit("Could not find `DISCORD_TOKEN` in the environment!")

        if asyncio.run(http_probe(token, config)):  # Check across discord if another client instance is running.
            asyncio.run(tui.start(DiscordClientConnector, token=token, config=config))
            return

        sys.exit("Could not find or authenticate to any raw/http bound sessions.")

    get_logger(
        "discord", "WARN", fmt="[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s"
    )

    # We're done probing, run a client.
    with Client(config=config, disable=disable) as client:
        client.run()


if __name__ == "__main__":
    main()
