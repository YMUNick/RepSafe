"""Test setup, same pattern as LineSleuth tests/conftest.py:
settings pinned to .env.example (a developer's .env cannot change results), offline modes forced,
and the network blocked, so any attempt to open or resolve a scam link fails the test."""
import os
import socket
from pathlib import Path

import pytest

for _line in (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8").splitlines():
    _key, _sep, _value = _line.partition("=")
    if _sep and _key.strip() and not _key.lstrip().startswith("#"):
        os.environ[_key.strip()] = _value.strip()
os.environ["AGENT_MODE"] = "offline_fixture"
os.environ["URL_REPUTATION_BACKEND"] = "fixture"

_LOOPBACK = ("localhost", "127.0.0.1", "::1")


def _is_loopback(host) -> bool:
    return host is None or (isinstance(host, str) and (host in _LOOPBACK or host.startswith("127.")))


@pytest.fixture(autouse=True, scope="session")
def _offline():
    """Any non-loopback connection or DNS lookup raises (loopback stays open for TestClient on Windows)."""
    real_connect, real_connect_ex, real_getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def blocked(address):
        return OSError(f"network access blocked in tests: {address!r}")

    def connect(self, address):
        if isinstance(address, tuple) and not _is_loopback(address[0]):
            raise blocked(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if isinstance(address, tuple) and not _is_loopback(address[0]):
            raise blocked(address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            raise blocked(host)
        return real_getaddrinfo(host, *args, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", connect)
        mp.setattr(socket.socket, "connect_ex", connect_ex)
        mp.setattr(socket, "getaddrinfo", getaddrinfo)
        yield
