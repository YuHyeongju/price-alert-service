"""감시(Watch) CRUD + 소유권 테스트."""


def test_create_and_list_watch(client, auth_headers):
    r = client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "에어팟 프로", "target_price": 300000},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["query"] == "에어팟 프로"
    assert data["target_price"] == 300000
    assert data["is_active"] is True

    r = client.get("/watches", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_and_delete_watch(client, auth_headers):
    wid = client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "노트북", "target_price": 1000000},
    ).json()["id"]

    r = client.patch(
        f"/watches/{wid}",
        headers=auth_headers,
        json={"target_price": 900000, "is_active": False},
    )
    assert r.status_code == 200
    assert r.json()["target_price"] == 900000
    assert r.json()["is_active"] is False

    r = client.delete(f"/watches/{wid}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/watches/{wid}", headers=auth_headers)
    assert r.status_code == 404


def test_cannot_access_others_watch(client, auth_headers):
    wid = client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "X", "target_price": 100},
    ).json()["id"]

    # 다른 사용자로 로그인해서 접근 시도 → 404 (소유권 격리)
    client.post("/auth/register", json={"email": "other@b.com", "password": "pw123456"})
    token = client.post(
        "/auth/login",
        data={"username": "other@b.com", "password": "pw123456"},
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}

    r = client.get(f"/watches/{wid}", headers=other_headers)
    assert r.status_code == 404


def test_manual_check_creates_alert_when_cheap(client, auth_headers):
    # 목표가를 아주 높게 잡으면 mock 가격이 항상 그 이하 → 알림 발생
    wid = client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "아무거나", "target_price": 99999999},
    ).json()["id"]

    r = client.post(f"/watches/{wid}/check", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["condition_met"] is True
    assert body["alert"] is not None

    # 알림 목록에도 쌓였는지
    r = client.get("/alerts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
