"""애플리케이션 설정.

pydantic-settings 를 사용해 환경변수(.env) 에서 값을 읽어옵니다.
외부 연동 키가 비어 있으면 각 서비스는 자동으로 mock 모드로 동작합니다.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "최저가 알림 서비스 (Price Alert Service)"

    # --- 인증 ---
    secret_key: str = "dev-insecure-secret-change-me-before-deploy"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24시간

    # --- 데이터베이스 ---
    database_url: str = "sqlite:///./pricewatch.db"
    auto_create_tables: bool = True  # 개발 편의용. 운영에선 Alembic 사용 권장.

    # --- 모니터링 엔진 / 스케줄러 ---
    enable_scheduler: bool = True
    check_interval_minutes: int = 10
    default_cooldown_minutes: int = 360  # 같은 감시건 재알림 최소 간격

    # --- 외부 연동 (비어 있으면 mock 모드) ---
    naver_client_id: str = ""
    naver_client_secret: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""  # OpenAI 호환 제공자로 교체 시 지정 (Groq/Gemini/Ollama)
    openai_model: str = "gpt-4o-mini"
    use_ai_filter: bool = True  # 검색 결과를 AI로 걸러 정확도↑ (AI 키 있을 때만 동작)
    discord_webhook_url: str = ""

    @property
    def naver_enabled(self) -> bool:
        return bool(self.naver_client_id and self.naver_client_secret)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
