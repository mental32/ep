from contextlib import suppress

import socket


def probe(address: str, port: int) -> bool:
    """Probe a system port by attempting to connect to it."""
    sock = socket.socket()

    try:
        sock.connect((address, port))
    except ConnectionRefusedError:
        return False
    else:
        return True
    finally:
        with suppress(Exception):
            sock.close()

def http_probe(token: str, channel_id: int) -> bool:
    """Probe a discord socket channel for a presence."""
    return False
