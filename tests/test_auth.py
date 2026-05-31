"""인증 흐름 테스트."""


def test_register_and_login(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@b.com"

    r = client.post("/auth/login", data={"username": "a@b.com", "password": "pw123456"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_duplicate_email_rejected(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    assert r.status_code == 409


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "wrong"})
    assert r.status_code == 401


def test_watches_require_auth(client):
    r = client.get("/watches")
    assert r.status_code == 401
