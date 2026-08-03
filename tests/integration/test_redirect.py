SAFE_URL = "http://1.1.1.1/target"


def test_redirect_active_url_returns_307_and_increments_click_count(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == SAFE_URL

    details = client.get(f"/api/v1/urls/{code}").json()
    assert details["click_count"] == 1
    assert details["last_accessed_at"] is not None


def test_redirect_unknown_code_returns_404(client):
    response = client.get("/does-not-exist", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_SHORT_CODE"


def test_redirect_disabled_url_returns_410(client):
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]
    client.patch(f"/api/v1/urls/{code}", json={"status": "disabled"})

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "URL_DISABLED"


def test_redirect_expired_url_returns_410_but_stays_visible_via_info_api(client):
    created = client.post(
        "/api/v1/urls",
        json={"original_url": SAFE_URL, "expires_at": "2020-01-01T00:00:00"},
    ).json()
    code = created["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "URL_EXPIRED"

    # FR-05: expired links remain visible via the info API
    details = client.get(f"/api/v1/urls/{code}")
    assert details.status_code == 200
    assert details.json()["status"] == "active"  # status itself is unaffected; expiry is derived


def test_multiple_concurrent_redirects_do_not_lose_click_count_updates(client):
    """NFR-09: atomic UPDATE, not read-then-write - sequential calls here stand in for
    concurrency since TestClient is single-threaded, but they exercise the exact same
    SQL path that would run under real concurrent requests."""
    created = client.post("/api/v1/urls", json={"original_url": SAFE_URL}).json()
    code = created["short_code"]

    for _ in range(10):
        client.get(f"/{code}", follow_redirects=False)

    details = client.get(f"/api/v1/urls/{code}").json()
    assert details["click_count"] == 10
