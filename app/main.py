"""FastAPI 앱 진입점."""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (create_all 전에 테이블 등록 보장)
from app.config import settings
from app.database import Base, engine
from app.routers import alerts, auth, watches
from app.scheduler import shutdown_scheduler, start_scheduler

# 콘솔 인코딩이 UTF-8 이 아닌 환경(예: Windows cp949)에서도 한글/이모지 로그가
# 깨지거나 UnicodeEncodeError 로 죽지 않도록 표준 출력 스트림을 UTF-8 로 맞춘다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 시작 ---
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.enable_scheduler:
        start_scheduler()
    yield
    # --- 종료 ---
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(watches.router)
app.include_router(alerts.router)

# 프론트엔드(정적 파일) 서빙
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    """간단한 웹 UI(정적 페이지)를 반환한다."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["meta"])
def health():
    """현재 어떤 모드로 동작 중인지 한눈에 보여준다."""
    return {
        "status": "ok",
        "price_source": "naver" if settings.naver_enabled else "mock",
        "ai": "openai" if settings.openai_enabled else "template",
        "notify": "discord" if settings.discord_enabled else "console",
        "scheduler": settings.enable_scheduler,
    }
