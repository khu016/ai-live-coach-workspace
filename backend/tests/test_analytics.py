def test_event_tracking_requires_login(raw_client):
    response = raw_client.post(
        "/api/v1/analytics/events",
        json={"event_name": "page_view", "route": "/"},
    )
    assert response.status_code == 401


def test_admin_dashboard_requires_separate_auth(client):
    response = client.get("/api/v1/admin/analytics/summary")
    assert response.status_code == 401


def test_admin_login_and_summary(client):
    bad = client.post("/api/v1/admin/login", json={"access_code": "wrong-code"})
    assert bad.status_code == 401

    logged_in = client.post(
        "/api/v1/admin/login", json={"access_code": "nivi-admin-test-code"}
    )
    assert logged_in.status_code == 200

    tracked = client.post(
        "/api/v1/analytics/events",
        json={
            "event_name": "page_view",
            "route": "/growth",
            "properties": {"invite_code": "must-not-save", "status": "ready"},
        },
    )
    assert tracked.status_code == 200

    summary = client.get("/api/v1/admin/analytics/summary?days=7")
    assert summary.status_code == 200
    body = summary.json()
    assert body["range_days"] == 7
    assert body["metrics"]["page_views"] == 1
    assert body["recent_events"][0]["properties"] == {"status": "ready"}


def test_unknown_event_is_rejected(client):
    response = client.post(
        "/api/v1/analytics/events",
        json={"event_name": "arbitrary_sensitive_capture", "route": "/"},
    )
    assert response.status_code == 400
