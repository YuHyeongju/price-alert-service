"""pytest 공통 픽스처.

주의: app 을 import 하기 *전에* 테스트용 환경변수를 설정한다.
(설정은 import 시점에 한 번 읽히기 때문)
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_pricewatch.db"
os.environ["ENABLE_SCHEDULER"] = "false"   # 테스트 중엔 스케줄러 끔
os.environ["NAVER_CLIENT_ID"] = ""          # mock 소스 강제
os.environ["NAVER_CLIENT_SECRET"] = ""
os.environ["OPENAI_API_KEY"] = ""           # 템플릿 코멘트 강제

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """각 테스트마다 깨끗한 스키마로 초기화."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers(client):
    """회원가입 + 로그인 후 Authorization 헤더를 돌려준다."""
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "secret123"},
    )
    resp = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "secret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
