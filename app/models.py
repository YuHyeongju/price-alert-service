"""SQLAlchemy ORM 모델 (User, Watch, Alert)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    watches: Mapped[list["Watch"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Watch(Base):
    """사용자가 등록한 '감시 조건' 한 건."""

    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    query: Mapped[str] = mapped_column(String(255))          # 검색어
    target_price: Mapped[int]                                # 목표가(원)
    comparison: Mapped[str] = mapped_column(String(8), default="lte")     # lte | gte
    channel: Mapped[str] = mapped_column(String(16), default="console")   # console | discord
    is_active: Mapped[bool] = mapped_column(default=True)
    cooldown_minutes: Mapped[int] = mapped_column(default=360)  # 재알림 최소 간격

    # 엔진이 갱신하는 상태값
    last_price: Mapped[int | None] = mapped_column(default=None)
    last_checked_at: Mapped[datetime | None] = mapped_column(default=None)
    last_notified_at: Mapped[datetime | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped["User"] = relationship(back_populates="watches")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="watch", cascade="all, delete-orphan"
    )


class Alert(Base):
    """조건이 충족되어 발송된 알림 이력 한 건."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_id: Mapped[int] = mapped_column(ForeignKey("watches.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    price: Mapped[int]                                       # 알림 시점 최저가
    product_title: Mapped[str] = mapped_column(String(500))
    product_link: Mapped[str] = mapped_column(String(1000), default="")
    mall_name: Mapped[str] = mapped_column(String(255), default="")
    message: Mapped[str] = mapped_column(String(2000), default="")  # AI 코멘트 포함 메시지

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    watch: Mapped["Watch"] = relationship(back_populates="alerts")
