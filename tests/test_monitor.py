"""모니터링 엔진 단위 테스트 (가짜 소스 + 시각 주입)."""
from datetime import timedelta

from app.models import User, Watch
from app.security import hash_password
from app.services.monitor import check_watch
from app.services.price_source import ProductResult
from app.utils import utcnow


class FakeSource:
    """항상 고정 가격을 돌려주는 테스트용 가격 소스."""

    def __init__(self, price: int):
        self.price = price

    def search(self, query: str):
        return [ProductResult(title=query, price=self.price, link="http://x", mall_name="m")]


def _make_watch(db, target=10000, comparison="lte", cooldown=360) -> Watch:
    user = User(email="m@m.com", hashed_password=hash_password("pw123456"))
    db.add(user)
    db.commit()
    db.refresh(user)
    watch = Watch(
        user_id=user.id,
        query="테스트상품",
        target_price=target,
        comparison=comparison,
        cooldown_minutes=cooldown,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def test_alert_created_when_condition_met(db):
    watch = _make_watch(db, target=10000)
    outcome = check_watch(db, watch, source=FakeSource(price=9000))
    assert outcome.condition_met is True
    assert outcome.alert is not None
    assert outcome.alert.price == 9000
    assert watch.last_price == 9000
    assert watch.last_notified_at is not None


def test_no_alert_when_condition_not_met(db):
    watch = _make_watch(db, target=10000)
    outcome = check_watch(db, watch, source=FakeSource(price=12000))
    assert outcome.condition_met is False
    assert outcome.alert is None
    assert watch.last_price == 12000
    assert watch.last_notified_at is None


def test_cooldown_prevents_duplicate(db):
    watch = _make_watch(db, target=10000, cooldown=360)
    now = utcnow()

    first = check_watch(db, watch, source=FakeSource(price=9000), now=now)
    assert first.alert is not None

    # 쿨다운(360분) 안에 다시 체크 → 조건은 충족하지만 알림 생략
    second = check_watch(db, watch, source=FakeSource(price=9000), now=now + timedelta(minutes=10))
    assert second.condition_met is True
    assert second.alert is None

    # 쿨다운이 지난 뒤 → 다시 알림
    third = check_watch(db, watch, source=FakeSource(price=9000), now=now + timedelta(minutes=400))
    assert third.alert is not None
