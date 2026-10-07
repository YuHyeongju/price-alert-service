"""모니터링 엔진 테스트.

check_watch 는 source/now 를 주입할 수 있어 네트워크·시계 없이 결정론적으로 검증한다.
"""
from datetime import timedelta

from app.models import User, Watch
from app.security import hash_password
from app.services.monitor import (
    check_all_active_watches,
    check_watch,
    _condition_met,
    _in_cooldown,
)
from app.services.price_source import ProductResult
from app.utils import utcnow


class FakeSource:
    """주어진 가격 하나를 돌려주는 가짜 가격 소스. price=None 이면 결과 없음."""

    def __init__(self, price):
        self.price = price

    def search(self, query):
        if self.price is None:
            return []
        return [ProductResult(title=f"{query} 정품", price=self.price, link="http://x", mall_name="몰")]


def _make_watch(db, target=100_000, comparison="lte", cooldown=360):
    user = User(email="m@x.com", hashed_password=hash_password("pw123456"))
    db.add(user)
    db.commit()
    db.refresh(user)
    watch = Watch(
        user_id=user.id, query="에어팟", target_price=target,
        comparison=comparison, channel="console", cooldown_minutes=cooldown,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


# ---------------- 순수 헬퍼 ----------------
def test_condition_met_lte_gte():
    assert _condition_met("lte", 90, 100) is True
    assert _condition_met("lte", 110, 100) is False
    assert _condition_met("gte", 110, 100) is True
    assert _condition_met("gte", 90, 100) is False
    assert _condition_met("lte", 100, 100) is True   # 경계 포함


def test_in_cooldown():
    now = utcnow()
    w = Watch(cooldown_minutes=360)
    w.last_notified_at = None
    assert _in_cooldown(w, now) is False                       # 알림 이력 없음
    w.last_notified_at = now - timedelta(minutes=5)
    assert _in_cooldown(w, now) is True                        # 5분 전 < 360분
    w.last_notified_at = now - timedelta(minutes=400)
    assert _in_cooldown(w, now) is False                       # 400분 전 > 360분


# ---------------- check_watch ----------------
def test_condition_met_creates_alert(db):
    watch = _make_watch(db, target=100_000, comparison="lte")
    outcome = check_watch(db, watch, source=FakeSource(90_000), now=utcnow())
    assert outcome.checked is True
    assert outcome.current_price == 90_000
    assert outcome.condition_met is True
    assert outcome.alert is not None
    assert watch.last_notified_at is not None
    assert watch.last_price == 90_000


def test_condition_not_met_no_alert(db):
    watch = _make_watch(db, target=100_000, comparison="lte")
    outcome = check_watch(db, watch, source=FakeSource(150_000), now=utcnow())
    assert outcome.checked is True
    assert outcome.condition_met is False
    assert outcome.alert is None
    assert watch.last_notified_at is None


def test_gte_comparison(db):
    watch = _make_watch(db, target=100_000, comparison="gte")
    outcome = check_watch(db, watch, source=FakeSource(120_000), now=utcnow())
    assert outcome.condition_met is True
    assert outcome.alert is not None


def test_empty_source_not_checked(db):
    watch = _make_watch(db)
    outcome = check_watch(db, watch, source=FakeSource(None), now=utcnow())
    assert outcome.checked is False
    assert outcome.current_price is None
    assert outcome.alert is None


def test_cooldown_prevents_duplicate_alert(db):
    watch = _make_watch(db, target=100_000, cooldown=360)
    t0 = utcnow()
    first = check_watch(db, watch, source=FakeSource(90_000), now=t0)
    assert first.alert is not None

    # 쿨다운 이내 재점검 → 조건은 충족하지만 알림 생략(멱등)
    again = check_watch(db, watch, source=FakeSource(90_000), now=t0 + timedelta(minutes=10))
    assert again.condition_met is True
    assert again.alert is None

    # 쿨다운 경과 후 → 새 알림 발생
    later = check_watch(db, watch, source=FakeSource(90_000), now=t0 + timedelta(minutes=361))
    assert later.alert is not None


# ---------------- check_all_active_watches ----------------
class BrokenSource:
    """특정 검색어에서만 예외를 던지는 소스 — 한 건 실패가 배치를 멈추는지 확인용."""

    def search(self, query):
        if query == "고장":
            raise RuntimeError("boom")
        return [ProductResult(title=f"{query} 정품", price=1_000, link="http://x", mall_name="몰")]


def test_check_all_skips_inactive_and_survives_errors(db):
    watch = _make_watch(db, target=100_000)               # 활성, 조건 충족 → 알림 1
    db.add_all([
        Watch(user_id=watch.user_id, query="꺼짐", target_price=100_000, comparison="lte",
              channel="console", cooldown_minutes=360, is_active=False),   # 비활성 → 무시
        Watch(user_id=watch.user_id, query="고장", target_price=100_000, comparison="lte",
              channel="console", cooldown_minutes=360),                    # 예외 → 건너뜀
    ])
    db.commit()
    assert check_all_active_watches(db, source=BrokenSource()) == 1
