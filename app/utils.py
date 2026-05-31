"""공통 유틸리티."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """타임존 정보가 없는(naive) UTC 현재 시각.

    SQLite 는 타임존을 저장하지 않으므로, 저장/비교에 쓰는 모든 시각을
    naive UTC 로 통일해 'aware vs naive' 비교 오류를 방지한다.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
