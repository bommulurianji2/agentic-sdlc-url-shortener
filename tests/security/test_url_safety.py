import pytest

from app.errors import AppError
from app.services.url_safety import (
    generate_short_code,
    validate_custom_alias,
    validate_original_url,
)

# A public IP literal. Python's ipaddress module treats RFC 5737 TEST-NET ranges
# as "private" (an IANA special-purpose registry decision, not just classic RFC1918),
# so a genuinely public, globally-routable literal is used instead. Using a literal
# (rather than a hostname) means socket.getaddrinfo does no real DNS/network lookup -
# it's purely local parsing - so this stays offline-safe.
SAFE_URL = "http://1.1.1.1/path"


def test_accepts_safe_http_url():
    assert validate_original_url(SAFE_URL) == SAFE_URL


def test_accepts_safe_https_url():
    url = "https://1.1.1.1/path"
    assert validate_original_url(url) == url


def test_rejects_disallowed_scheme():
    with pytest.raises(AppError) as exc:
        validate_original_url("ftp://1.1.1.1/file")
    assert exc.value.code == "UNSAFE_SCHEME"


def test_rejects_javascript_scheme():
    with pytest.raises(AppError) as exc:
        validate_original_url("javascript:alert(1)")
    assert exc.value.code in {"UNSAFE_SCHEME", "INVALID_URL"}


def test_rejects_empty_url():
    with pytest.raises(AppError) as exc:
        validate_original_url("")
    assert exc.value.code == "INVALID_URL"


def test_rejects_oversized_url():
    with pytest.raises(AppError) as exc:
        validate_original_url("http://1.1.1.1/" + "a" * 3000)
    assert exc.value.code == "INVALID_URL"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/path",
        "http://127.0.0.1/path",
        "http://10.0.0.5/path",
        "http://172.16.0.5/path",
        "http://192.168.1.5/path",
        "http://169.254.1.1/path",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/path",
    ],
)
def test_rejects_private_and_metadata_destinations(url):
    with pytest.raises(AppError) as exc:
        validate_original_url(url)
    assert exc.value.code == "BLOCKED_PRIVATE_DESTINATION"


def test_accepts_valid_custom_alias():
    assert validate_custom_alias("my-link_1") == "my-link_1"


def test_rejects_too_short_alias():
    with pytest.raises(AppError) as exc:
        validate_custom_alias("ab")
    assert exc.value.code == "VALIDATION_FAILURE"


def test_rejects_alias_with_invalid_characters():
    with pytest.raises(AppError) as exc:
        validate_custom_alias("bad alias!")
    assert exc.value.code == "VALIDATION_FAILURE"


@pytest.mark.parametrize("alias", ["health", "docs", "api", "openapi.json"])
def test_rejects_reserved_alias(alias):
    with pytest.raises(AppError) as exc:
        validate_custom_alias(alias)
    assert exc.value.code == "VALIDATION_FAILURE"


def test_short_code_is_correct_length_and_url_safe():
    code = generate_short_code(7)
    assert len(code) == 7
    assert all(c.isalnum() or c in "-_" for c in code)


def test_short_code_generation_is_not_deterministic():
    codes = {generate_short_code(7) for _ in range(20)}
    assert len(codes) == 20
