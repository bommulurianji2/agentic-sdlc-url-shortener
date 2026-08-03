import ipaddress
import re
import secrets
import socket
from urllib.parse import urlparse

from app.errors import blocked_private_destination, invalid_url, unsafe_scheme, validation_failure

ALLOWED_SCHEMES = {"http", "https"}

CLOUD_METADATA_HOSTS = {
    "169.254.169.254",  # AWS / Azure / GCP metadata endpoint
    "metadata.google.internal",
    "fd00:ec2::254",  # AWS IMDSv2 IPv6
}

RESERVED_ALIASES = {"api", "health", "docs", "redoc", "openapi.json"}
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def validate_original_url(raw_url: str) -> str:
    """NFR-01: scheme allowlist + SSRF/private-network blocking, checked once at creation time."""
    if not raw_url or len(raw_url) > 2048:
        raise invalid_url("URL must be 1-2048 characters.")

    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        raise invalid_url("URL must be an absolute URL with a scheme and host.")

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise unsafe_scheme(f"Scheme '{parsed.scheme}' is not allowed; only http/https.")

    hostname = parsed.hostname
    if not hostname:
        raise invalid_url("URL is missing a hostname.")

    if _is_blocked_host(hostname):
        raise blocked_private_destination()

    return raw_url


def _is_blocked_host(hostname: str) -> bool:
    hostname_lower = hostname.lower()
    if hostname_lower == "localhost" or hostname_lower in CLOUD_METADATA_HOSTS:
        return True

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise invalid_url(f"Could not resolve host '{hostname}'.") from None

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            addr.is_loopback
            or addr.is_private
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or str(addr) in CLOUD_METADATA_HOSTS
        ):
            return True
    return False


def validate_custom_alias(alias: str) -> str:
    """FR-07: allowed characters, length, and reserved-name checks. Uniqueness is
    checked separately at the repository layer, where the DB has the authoritative view."""
    if not ALIAS_PATTERN.match(alias):
        raise validation_failure(
            "Custom alias must be 3-32 characters: letters, digits, '_' or '-'."
        )
    if alias.lower() in RESERVED_ALIASES:
        raise validation_failure(f"Alias '{alias}' is reserved.")
    return alias


def generate_short_code(length: int = 7) -> str:
    """NFR-02: cryptographically secure short-code generation."""
    return secrets.token_urlsafe(length)[:length]
