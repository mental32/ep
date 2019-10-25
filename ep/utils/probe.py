import socket


def probe(address: str, port: int) -> bool:
    """Probe a system port by attempting to connect to it."""
    sock = socket.socket()

    try:
        with sock.connect((address, port)):
            return True
    except ConnectionRefusedError:
        return False


def http_probe(token: str, channel_id: int) -> bool:
    """Probe a discord socket channel for a presence."""
    return False
