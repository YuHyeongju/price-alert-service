"""인증 엔드포인트 + 보안 유닛(해시/JWT) 테스트."""
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


# ---------------- 엔드포인트 ----------------
def test_register_returns_201_and_user(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    assert "id" in body
    assert "hashed_password" not in body  # 해시는 응답에 노출되지 않음


def test_login_returns_bearer_token(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "pw123456"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


def test_duplicate_email_rejected(client):
    client.post("/auth/register", json={"email": "dup@b.com", "password": "pw123456"})
    r = client.post("/auth/register", json={"email": "dup@b.com", "password": "pw123456"})
    assert r.status_code == 409


def test_login_wrong_password_401(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "pw123456"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "nope"})
    assert r.status_code == 401


def test_short_password_rejected_422(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "123"})
    assert r.status_code == 422  # min_length=6


def test_protected_endpoint_requires_auth(client):
    assert client.get("/watches").status_code == 401
    assert client.get("/alerts").status_code == 401


# ---------------- 보안 유닛 ----------------
def test_password_hash_roundtrip():
    h = hash_password("s3cret!")
    assert h != "s3cret!"                 # 평문 저장 아님
    assert verify_password("s3cret!", h)  # 올바른 비번 통과
    assert not verify_password("wrong", h)


def test_password_hash_is_salted():
    # 같은 비밀번호라도 매번 다른 해시(솔트) — 둘 다 검증은 통과
    h1, h2 = hash_password("same"), hash_password("same")
    assert h1 != h2
    assert verify_password("same", h1) and verify_password("same", h2)


def test_jwt_roundtrip_and_invalid():
    token = create_access_token("42")
    assert decode_token(token) == "42"
    assert decode_token("not.a.jwt") is None
    assert decode_token(token + "tampered") is None
