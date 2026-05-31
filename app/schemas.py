"""Pydantic 입출력 스키마 (요청/응답 검증)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Comparison = Literal["lte", "gte"]   # lte: 이하면 알림, gte: 이상이면 알림
Channel = Literal["console", "discord"]


# --- 인증 ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- 감시(Watch) ---
class WatchCreate(BaseModel):
    query: str = Field(min_length=1, max_length=255, examples=["에어팟 프로 2세대"])
    target_price: int = Field(gt=0, description="목표가(원). 이 값과 비교해 알림", examples=[270000])
    comparison: Comparison = "lte"
    channel: Channel = "console"
    cooldown_minutes: Optional[int] = Field(default=None, ge=0, description="없으면 서버 기본값 사용")


class WatchUpdate(BaseModel):
    query: Optional[str] = Field(default=None, min_length=1, max_length=255)
    target_price: Optional[int] = Field(default=None, gt=0)
    comparison: Optional[Comparison] = None
    channel: Optional[Channel] = None
    is_active: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(default=None, ge=0)


class WatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    query: str
    target_price: int
    comparison: Comparison
    channel: Channel
    is_active: bool
    cooldown_minutes: int
    last_price: Optional[int]
    last_checked_at: Optional[datetime]
    last_notified_at: Optional[datetime]
    created_at: datetime


# --- 알림(Alert) ---
class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    watch_id: int
    price: int
    product_title: str
    product_link: str
    mall_name: str
    message: str
    created_at: datetime


class CheckResult(BaseModel):
    """수동 체크(POST /watches/{id}/check) 응답."""
    checked: bool
    current_price: Optional[int]
    condition_met: bool
    alert: Optional[AlertOut] = None
    detail: str = ""
