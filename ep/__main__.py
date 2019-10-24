import sys
import pathlib

import click

import ep
from ep.core import WebsocketServer


@click.command()
@click.option("-c", "--config", type=pathlib.Path)
@click.option("-C", "--generate-config", is_flag=True)
@click.option("--probe", is_flag=True)
@click.option("--disable", is_flag=True)
@click.option("--port", type=int, default=WebsocketServer.port)
@click.option("--addr", type=str, default=WebsocketServer.host)
def main(**kwargs):
    addr = kwargs["addr"]
    port = kwargs["port"]

    if ep.probe(addr, port):
        # There is another client running and bound to this port.
        return ep.tui.start(addr=addr, port=port)

    config = kwargs["config"]

    if config is None:
        sys.exit("Please supply a configuration file.")

    if ep.http_probe(config=config):
        return ep.tui.start(addr=addr, port=port)

    # We're done probing run a client.
    disable = kwargs["disable"]
    with ep.Client(config=config, disable=disable) as client:
        client.run()


if __name__ == "__main__":
    main()
