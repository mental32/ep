import sys
import pathlib

import click

import ep
from ep import Client, Config, WebsocketServer, probe, http_probe


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

    addr = kwargs["addr"]
    port = kwargs["port"]

    if probe(addr, port):
        # There is another client running and bound to this port.
        return ep.tui.start(addr=addr, port=port)

    config = kwargs["config"]

    if config is None:
        sys.exit("Please supply a configuration file.")

    config = Config.from_file(config)
    disable = kwargs["disable"]

    if not disable and http_probe("", config["ep"]["socket_channel"]):
        # Check across discord if another client instance is running.
        return ep.tui.start(addr=addr, port=port)

    # We're done probing run a client.
    with Client(config=config, disable=disable) as client:
        client.run()


if __name__ == "__main__":
    main()
