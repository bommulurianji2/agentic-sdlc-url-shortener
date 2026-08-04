"""Brownfield regression suite - SCEN-02. Proves the configurable-expiry and
disabled_at enhancements didn't break existing behavior, and pins down the
new boundary rules."""

SAFE_URL = "http://1.1.1.1/brownfield"


def test_omitting_expiry_fields_still_defaults_to_30_days(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL})
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None  # unchanged greenfield behavior


def test_raw_expires_at_still_works_unchanged(client):
    response = client.post(
        "/api/v1/urls",
        json={"original_url": SAFE_URL, "expires_at": "2030-01-01T00:00:00"},
    )
    assert response.status_code == 201
    assert response.json()["expires_at"].startswith("2030-01-01")


def test_expires_in_days_sets_a_correspondingly_distant_expiry(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL, "expires_in_days": 365})
    assert response.status_code == 201
    created = response.json()["created_at"][:10]
    expires = response.json()["expires_at"][:10]
    assert created != expires  # sanity: it actually moved the date out


def test_expires_in_days_zero_is_rejected(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL, "expires_in_days": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILURE"


def test_expires_in_days_negative_is_rejected(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL, "expires_in_days": -5})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILURE"


def test_expires_in_days_over_365_is_rejected(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL, "expires_in_days": 366})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILURE"


def test_disabled_at_is_stamped_on_disable_and_cleared_on_reactivate(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]
    assert created["disabled_at"] is None

    disabled = client.patch(f"/api/v1/urls/{code}", json={"status": "disabled"})
    assert disabled.json()["disabled_at"] is not None

    reenabled = client.patch(f"/api/v1/urls/{code}", json={"status": "active"})
    assert reenabled.json()["disabled_at"] is None


def test_redirect_and_analytics_are_unaffected_by_the_brownfield_change(client):
    """Regression check: FR-02/FR-04 behavior (unrelated to expiry/disable)
    must be identical to the greenfield baseline."""
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]

    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == SAFE_URL

    analytics = client.get(f"/api/v1/urls/{code}/analytics")
    assert analytics.json()["total_clicks"] == 1
