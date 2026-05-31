"""데이터베이스 연결 / 세션 / Base 정의."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite 는 기본적으로 한 스레드에서만 커넥션을 쓰게 막혀 있다.
# FastAPI(스레드풀) + 스케줄러(별도 스레드) 에서 함께 쓰기 위해 옵션을 푼다.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 의존성: 요청 동안만 세션을 열고 끝나면 닫는다."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
