def _training_payload():
    return {
        "live_type": "带货",
        "goal": "测试数据隔离",
        "practice_mode": "focus",
        "media_kind": "audio",
    }


def test_protected_api_requires_login(raw_client):
    response = raw_client.get("/api/v1/trainings")
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录"


def test_invalid_invite_is_rejected(raw_client):
    response = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "陌生主播", "invite_code": "wrong-code"},
    )
    assert response.status_code == 401
    bypass = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "陌生主播", "invite_code": "invalid-invite"},
    )
    assert bypass.status_code == 401


def test_invite_login_sets_httponly_session(raw_client):
    response = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "小鹿主播", "invite_code": "nivi-test-one"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["nickname"] == "小鹿主播"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert raw_client.get("/api/v1/auth/me").status_code == 200


def test_users_cannot_read_each_others_training(raw_client):
    first_login = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "主播甲", "invite_code": "nivi-test-one"},
    )
    assert first_login.status_code == 200
    training_id = raw_client.post(
        "/api/v1/trainings", json=_training_payload()
    ).json()["training"]["id"]

    assert raw_client.post("/api/v1/auth/logout").status_code == 200
    second_login = raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "主播乙", "invite_code": "nivi-test-two"},
    )
    assert second_login.status_code == 200
    assert raw_client.get(f"/api/v1/trainings/{training_id}").status_code == 404
    assert raw_client.delete(f"/api/v1/trainings/{training_id}").status_code == 404
    assert raw_client.get("/api/v1/trainings").json()["trainings"] == []
    assert raw_client.get("/api/v1/recordings").json()["recordings"] == []
    assert raw_client.get("/api/v1/stats/week").json()["week"]["training_count"] == 0


def test_tutorial_progress_is_isolated_by_user(raw_client):
    raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "主播甲", "invite_code": "nivi-test-one"},
    )
    completed = raw_client.put(
        "/api/v1/tutorials/opening-30s/progress", json={"completed": True}
    )
    assert completed.status_code == 200
    assert "opening-30s" in completed.json()["summary"]["completed_ids"]

    raw_client.post("/api/v1/auth/logout")
    raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "主播乙", "invite_code": "nivi-test-two"},
    )
    progress = raw_client.get("/api/v1/tutorials/progress")
    assert progress.status_code == 200
    assert progress.json()["completed_ids"] == []


def test_logout_revokes_session(raw_client):
    raw_client.post(
        "/api/v1/auth/invite",
        json={"nickname": "测试主播", "invite_code": "nivi-test-one"},
    )
    assert raw_client.post("/api/v1/auth/logout").status_code == 200
    assert raw_client.get("/api/v1/auth/me").status_code == 401
