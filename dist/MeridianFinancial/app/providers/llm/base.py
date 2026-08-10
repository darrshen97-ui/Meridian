"""LLMProvider protocol (brief §12).

The AI layer talks only to a model on this machine by default. OllamaProvider is
the active implementation; AnthropicProvider exists behind the same interface,
disabled unless explicitly configured, and clearly labeled as off-device.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


@dataclass
class LLMResponse:
    parsed: dict
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class LLMError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LLMUnavailable(LLMError):
    """The model isn't reachable/installed — AI features degrade, never break."""


class LLMProvider(Protocol):
    key: str
    sends_data_off_device: bool

    async def status(self) -> dict: ...

    async def complete_json(self, *, system: str, user: str, schema: dict) -> LLMResponse:
        """One job per call, JSON-schema constrained output."""
        ...


def endpoint_is_loopback(url: str) -> bool:
    """True only if the endpoint host resolves to a loopback address.

    Non-negotiable #5: financial data never leaves the machine. The default AI
    path refuses to run against anything that isn't 127.0.0.1/::1.
    """
    host = urlparse(url).hostname
    if host is None:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    return all(
        ipaddress.ip_address(info[4][0]).is_loopback for info in infos
    )
