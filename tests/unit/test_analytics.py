from app.services.analytics import categorize_user_agent, extract_referrer_domain


def test_categorize_user_agent_none_returns_none():
    assert categorize_user_agent(None) is None


def test_categorize_user_agent_detects_bots():
    assert categorize_user_agent("curl/8.0") == "bot"
    assert categorize_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") == "bot"


def test_categorize_user_agent_detects_browsers():
    assert (
        categorize_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"
        )
        == "browser"
    )


def test_categorize_user_agent_falls_back_to_other():
    assert categorize_user_agent("SomeUnknownClient/1.0") == "other"


def test_extract_referrer_domain_none_returns_none():
    assert extract_referrer_domain(None) is None


def test_extract_referrer_domain_extracts_netloc_only():
    assert extract_referrer_domain("https://example.com/some/path?query=1") == "example.com"


def test_extract_referrer_domain_handles_malformed_referrer():
    assert extract_referrer_domain("not-a-url") is None
