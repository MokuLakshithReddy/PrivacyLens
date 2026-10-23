from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp
from aiohttp.abc import AbstractResolver

MAX_POLICY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
ALLOWED_PORTS = {"http": {80}, "https": {443}}
ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}


class PolicyFetchError(ValueError):
    """A safe, client-displayable policy retrieval failure."""


@dataclass(frozen=True)
class FetchedPolicy:
    text: str
    final_url: str
    content_type: str
    status: int


def _public_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise PolicyFetchError("Policy host resolved to an invalid address") from exc
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        raise PolicyFetchError("Policy host resolved to a disallowed address")
    if not address.is_global:
        raise PolicyFetchError("Policy host resolved to a non-public address")
    return address


def normalize_policy_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port
    except (ValueError, AttributeError) as exc:
        raise PolicyFetchError("Policy URL is invalid") from exc
    if scheme not in ALLOWED_PORTS or not host or parsed.username or parsed.password:
        raise PolicyFetchError("Policy URL must use HTTP or HTTPS and must not contain credentials")
    host = host.rstrip(".").lower()
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise PolicyFetchError("Policy host is not public")
    try:
        ip_literal = ipaddress.ip_address(host)
    except ValueError:
        ip_literal = None
    if ip_literal is not None and not ip_literal.is_global:
        raise PolicyFetchError("Policy host is not public")
    if port is not None and port not in ALLOWED_PORTS[scheme]:
        raise PolicyFetchError("Policy URL uses a disallowed port")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise PolicyFetchError("Policy hostname is invalid") from exc
    # Reject legacy numeric IP spellings that parsers or resolvers may interpret differently.
    if all(ch in "0123456789." for ch in host) and host.count(".") != 3:
        raise PolicyFetchError("Policy URL uses an ambiguous numeric address")
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))


def storage_safe_url(value: str) -> str:
    """Remove query and fragment data before retaining a source URL."""
    normalized = normalize_policy_url(value)
    parsed = urlsplit(normalized)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


class PublicResolver(AbstractResolver):
    """Resolve every connection once, reject special-use addresses, and pin results."""

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_UNSPEC):
        loop = asyncio.get_running_loop()
        try:
            answers = await loop.getaddrinfo(host, port, family=family, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise OSError("Policy host could not be resolved") from exc
        unique: dict[str, tuple[int, str]] = {}
        for answer_family, _type, proto, _canonname, sockaddr in answers:
            ip = str(_public_ip(sockaddr[0]))
            unique[ip] = (answer_family, ip)
        if not unique:
            raise OSError("Policy host has no usable public address")
        return [
            {"hostname": host, "host": ip, "port": port, "family": fam,
             "proto": socket.IPPROTO_TCP, "flags": socket.AI_NUMERICHOST}
            for fam, ip in unique.values()
        ]

    async def close(self) -> None:
        return None


async def fetch_public_policy(url: str) -> FetchedPolicy:
    current = normalize_policy_url(url)
    timeout = aiohttp.ClientTimeout(total=12, connect=4, sock_read=7)
    headers = {"Accept": "text/html, text/plain, application/xhtml+xml"}

    for redirect_count in range(MAX_REDIRECTS + 1):
        resolver = PublicResolver()
        connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False, limit=1)
        try:
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout, headers=headers,
                auto_decompress=True, trust_env=False,
            ) as session:
                async with session.get(current, allow_redirects=False) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_count >= MAX_REDIRECTS:
                            raise PolicyFetchError("Policy URL redirected too many times")
                        current = normalize_policy_url(urljoin(current, location))
                        continue
                    if response.status < 200 or response.status >= 300:
                        raise PolicyFetchError("Policy server returned an unsuccessful response")
                    content_type = response.content_type.lower()
                    if content_type not in ALLOWED_CONTENT_TYPES:
                        raise PolicyFetchError("Policy server returned an unsupported content type")
                    if response.content_length is not None and response.content_length > MAX_POLICY_BYTES:
                        raise PolicyFetchError("Policy response exceeds the size limit")
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.content.iter_chunked(16 * 1024):
                        total += len(chunk)
                        if total > MAX_POLICY_BYTES:
                            raise PolicyFetchError("Policy response exceeds the size limit")
                        chunks.append(chunk)
                    text = b"".join(chunks).decode(response.charset or "utf-8", errors="replace")
                    return FetchedPolicy(text, current, content_type, response.status)
        except PolicyFetchError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, UnicodeError) as exc:
            # Never return DNS answers, internal addresses, request headers, or stack details.
            raise PolicyFetchError("Policy server could not be reached safely") from exc
    raise PolicyFetchError("Policy URL redirected too many times")
