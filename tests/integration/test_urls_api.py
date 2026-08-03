SAFE_URL = "http://1.1.1.1/some/path"


def test_create_url_returns_expected_shape(client):
    response = client.post("/api/v1/urls", json={"original_url": SAFE_URL})
    assert response.status_code == 201
    body = response.json()
    assert body["original_url"] == SAFE_URL
    assert body["status"] == "active"
    assert body["click_count"] == 0
    assert body["expires_at"] is not None  # FR-01/05: defaults to 30 days, never null
    assert body["short_code"] in body["short_url"]


def test_create_url_with_custom_alias(client):
    response = client.post(
        "/api/v1/urls", json={"original_url": SAFE_URL, "custom_alias": "my-alias-1"}
    )
    assert response.status_code == 201
    assert response.json()["short_code"] == "my-alias-1"


def test_create_url_with_duplicate_alias_is_rejected(client):
    client.post("/api/v1/urls", json={"original_url": SAFE_URL, "custom_alias": "dup-alias"})
    response = client.post(
        "/api/v1/urls", json={"original_url": SAFE_URL, "custom_alias": "dup-alias"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_ALIAS"


def test_create_url_with_unsafe_scheme_is_rejected(client):
    response = client.post("/api/v1/urls", json={"original_url": "ftp://1.1.1.1/file"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSAFE_SCHEME"


def test_create_url_with_private_destination_is_rejected(client):
    response = client.post("/api/v1/urls", json={"original_url": "http://127.0.0.1/x"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "BLOCKED_PRIVATE_DESTINATION"


def test_create_url_with_reserved_alias_is_rejected(client):
    response = client.post(
        "/api/v1/urls", json={"original_url": SAFE_URL, "custom_alias": "health"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILURE"


def test_get_url_details(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    response = client.get(f"/api/v1/urls/{created['short_code']}")
    assert response.status_code == 200
    assert response.json()["original_url"] == SAFE_URL


def test_get_unknown_url_details_returns_404(client):
    response = client.get("/api/v1/urls/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_SHORT_CODE"


def test_disable_and_reenable_url(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]

    disabled = client.patch(f"/api/v1/urls/{code}", json={"status": "disabled"})
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    reenabled = client.patch(f"/api/v1/urls/{code}", json={"status": "active"})
    assert reenabled.status_code == 200
    assert reenabled.json()["status"] == "active"


def test_patch_unknown_url_returns_404(client):
    response = client.patch("/api/v1/urls/does-not-exist", json={"status": "disabled"})
    assert response.status_code == 404


def test_analytics_starts_empty_then_reflects_a_click(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]

    empty = client.get(f"/api/v1/urls/{code}/analytics")
    assert empty.status_code == 200
    assert empty.json()["total_clicks"] == 0
    assert empty.json()["click_events"] == []

    client.get(f"/{code}", follow_redirects=False)

    after = client.get(f"/api/v1/urls/{code}/analytics")
    assert after.json()["total_clicks"] == 1
    assert len(after.json()["click_events"]) == 1


def test_analytics_for_unknown_code_returns_404(client):
    response = client.get("/api/v1/urls/does-not-exist/analytics")
    assert response.status_code == 404
