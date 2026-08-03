from urllib.parse import urlparse

_BOT_MARKERS = ("bot", "crawler", "spider", "curl", "wget", "python-requests")


def categorize_user_agent(user_agent: str | None) -> str | None:
    """NFR-03: store only a coarse category, never the raw User-Agent string."""
    if not user_agent:
        return None
    lowered = user_agent.lower()
    if any(marker in lowered for marker in _BOT_MARKERS):
        return "bot"
    if "mozilla" in lowered or "chrome" in lowered or "safari" in lowered:
        return "browser"
    return "other"


def extract_referrer_domain(referrer: str | None) -> str | None:
    """NFR-03: store only the referrer's domain, never the full referrer URL
    (which could contain query strings/paths with sensitive data)."""
    if not referrer:
        return None
    parsed = urlparse(referrer)
    return parsed.netloc or None
