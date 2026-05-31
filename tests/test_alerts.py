"""알림 조회/삭제 테스트."""


def _make_alert(client, headers):
    """목표가를 크게 잡아 알림을 1건 만들고 그 id를 반환."""
    wid = client.post(
        "/watches", headers=headers,
        json={"query": "x", "target_price": 99999999},
    ).json()["id"]
    client.post(f"/watches/{wid}/check", headers=headers)
    return client.get("/alerts", headers=headers).json()[0]["id"]


def test_delete_one_alert(client, auth_headers):
    aid = _make_alert(client, auth_headers)
    r = client.delete(f"/alerts/{aid}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get("/alerts", headers=auth_headers).json() == []


def test_clear_all_alerts(client, auth_headers):
    _make_alert(client, auth_headers)
    _make_alert(client, auth_headers)
    assert len(client.get("/alerts", headers=auth_headers).json()) >= 1

    r = client.delete("/alerts", headers=auth_headers)
    assert r.status_code == 204
    assert client.get("/alerts", headers=auth_headers).json() == []


def test_cannot_delete_others_alert(client, auth_headers):
    aid = _make_alert(client, auth_headers)

    client.post("/auth/register", json={"email": "o@o.com", "password": "pw123456"})
    token = client.post(
        "/auth/login", data={"username": "o@o.com", "password": "pw123456"}
    ).json()["access_token"]
    other = {"Authorization": f"Bearer {token}"}

    r = client.delete(f"/alerts/{aid}", headers=other)
    assert r.status_code == 404
    # 원래 주인의 알림은 그대로 남아 있어야 한다
    assert len(client.get("/alerts", headers=auth_headers).json()) == 1
