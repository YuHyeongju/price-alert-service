"""감시(Watch) CRUD + 소유권 격리 엔드포인트 테스트."""


def _headers_for(client, email):
    client.post("/auth/register", json={"email": email, "password": "pw123456"})
    tok = client.post("/auth/login", data={"username": email, "password": "pw123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_create_watch(client, auth_headers):
    r = client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "에어팟 프로 2", "target_price": 270000, "comparison": "lte"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["query"] == "에어팟 프로 2"
    assert body["target_price"] == 270000
    assert body["comparison"] == "lte"
    assert body["is_active"] is True


def test_create_watch_defaults_cooldown(client, auth_headers):
    r = client.post("/watches", headers=auth_headers, json={"query": "키보드", "target_price": 50000})
    assert r.status_code == 201
    assert r.json()["cooldown_minutes"] > 0  # 서버 기본값 채워짐


def test_invalid_target_price_rejected(client, auth_headers):
    r = client.post("/watches", headers=auth_headers, json={"query": "x", "target_price": 0})
    assert r.status_code == 422  # gt=0


def test_list_and_get_watch(client, auth_headers):
    created = client.post("/watches", headers=auth_headers, json={"query": "모니터", "target_price": 300000}).json()
    lst = client.get("/watches", headers=auth_headers)
    assert lst.status_code == 200
    assert any(w["id"] == created["id"] for w in lst.json())

    one = client.get(f"/watches/{created['id']}", headers=auth_headers)
    assert one.status_code == 200
    assert one.json()["id"] == created["id"]


def test_update_watch(client, auth_headers):
    wid = client.post("/watches", headers=auth_headers, json={"query": "q", "target_price": 100}).json()["id"]
    r = client.patch(f"/watches/{wid}", headers=auth_headers, json={"target_price": 999, "is_active": False})
    assert r.status_code == 200
    assert r.json()["target_price"] == 999
    assert r.json()["is_active"] is False


def test_delete_watch(client, auth_headers):
    wid = client.post("/watches", headers=auth_headers, json={"query": "q", "target_price": 100}).json()["id"]
    assert client.delete(f"/watches/{wid}", headers=auth_headers).status_code == 204
    assert client.get(f"/watches/{wid}", headers=auth_headers).status_code == 404


def test_ownership_isolation(client):
    alice = _headers_for(client, "alice@x.com")
    bob = _headers_for(client, "bob@x.com")
    wid = client.post("/watches", headers=alice, json={"query": "비밀", "target_price": 100}).json()["id"]

    # 밥은 앨리스의 감시를 못 본다 (404)
    assert client.get(f"/watches/{wid}", headers=bob).status_code == 404
    assert client.delete(f"/watches/{wid}", headers=bob).status_code == 404
    # 밥의 목록엔 앨리스 것이 없다
    assert all(w["id"] != wid for w in client.get("/watches", headers=bob).json())
