"""모니터링 엔진: 감시 조건을 평가하고, 충족 시 알림을 만든다.

핵심 백엔드 포인트
- 조건 평가 (lte/gte)
- 멱등성/쿨다운: 같은 감시건을 cooldown_minutes 안에 중복 알림하지 않는다.
- 외부 소스/현재시각을 '주입' 가능하게 해서 테스트하기 쉽게 만든다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Watch
from app.services import ai, notifier
from app.services.price_source import PriceSource, cheapest, get_price_source
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class CheckOutcome:
    checked: bool                  # 가격 조회 성공 여부
    current_price: Optional[int]   # 조회된 최저가
    condition_met: bool            # 목표가 조건 충족 여부
    alert: Optional[Alert]         # 새로 생성된 알림(없으면 None)
    detail: str = ""               # 사람이 읽을 설명


def _condition_met(comparison: str, price: int, target: int) -> bool:
    return price <= target if comparison == "lte" else price >= target


def _in_cooldown(watch: Watch, now: datetime) -> bool:
    if watch.last_notified_at is None:
        return False
    return now - watch.last_notified_at < timedelta(minutes=watch.cooldown_minutes)


def check_watch(
    db: Session,
    watch: Watch,
    source: Optional[PriceSource] = None,
    now: Optional[datetime] = None,
) -> CheckOutcome:
    """감시 한 건을 평가한다. (source/now 를 주입하면 테스트가 쉬워진다)"""
    source = source or get_price_source()
    now = now or utcnow()

    results = source.search(watch.query)
    relevant = ai.select_relevant_products(watch.query, results)  # AI 정확도 필터
    product = cheapest(relevant)

    # 결과와 무관하게 '마지막 확인 시각'은 항상 갱신한다.
    watch.last_checked_at = now

    if product is None:
        db.commit()
        return CheckOutcome(False, None, False, None, "가격을 가져오지 못했습니다.")

    watch.last_price = product.price

    if not _condition_met(watch.comparison, product.price, watch.target_price):
        db.commit()
        return CheckOutcome(
            True, product.price, False, None, "조건 미충족 (목표가에 도달하지 않음)."
        )

    # 조건 충족 → 단, 쿨다운 중이면 재알림하지 않는다 (멱등성/스팸 방지)
    if _in_cooldown(watch, now):
        db.commit()
        return CheckOutcome(
            True, product.price, True, None, "조건 충족했으나 쿨다운 중이라 알림 생략."
        )

    # 알림 생성 + 발송
    message = ai.generate_comment(watch.query, product.price, watch.target_price)
    alert = Alert(
        watch_id=watch.id,
        user_id=watch.user_id,
        price=product.price,
        product_title=product.title,
        product_link=product.link,
        mall_name=product.mall_name,
        message=message,
    )
    db.add(alert)
    watch.last_notified_at = now
    db.commit()
    db.refresh(alert)

    notifier.notify(
        channel=watch.channel,
        title=f"{watch.query} 목표가 도달!",
        message=message,
        link=product.link,
    )
    return CheckOutcome(True, product.price, True, alert, "알림을 생성했습니다.")


def check_all_active_watches(db: Session, source: Optional[PriceSource] = None) -> int:
    """활성 감시건 전체를 평가한다. 생성된 알림 수를 반환."""
    source = source or get_price_source()
    watches = db.scalars(select(Watch).where(Watch.is_active.is_(True))).all()
    created = 0
    for watch in watches:
        try:
            outcome = check_watch(db, watch, source=source)
            if outcome.alert is not None:
                created += 1
        except Exception:  # 한 건 실패가 배치 전체를 멈추면 안 된다
            logger.exception("감시 평가 중 오류 (watch_id=%s)", watch.id)
            db.rollback()
    if watches:
        logger.info("모니터링 1회 완료: %d건 점검, %d건 알림", len(watches), created)
    return created
