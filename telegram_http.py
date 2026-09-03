"""Telegram-only IPv4-preferred urllib transport."""
from contextlib import contextmanager
import socket
import urllib.request

@contextmanager
def ipv4_first():
    original = socket.getaddrinfo
    def getaddrinfo(host, port, *args, **kwargs):
        results = original(host, port, *args, **kwargs)
        ipv4 = [item for item in results if item[0] == socket.AF_INET]
        return ipv4 + [item for item in results if item[0] != socket.AF_INET]
    socket.getaddrinfo = getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original

def urlopen(request, timeout):
    with ipv4_first():
        return urllib.request.urlopen(request, timeout=timeout)
