"""감시(Watch) CRUD + 수동 체크 라우터. 모두 로그인 필요."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User, Watch
from app.schemas import CheckResult, WatchCreate, WatchOut, WatchUpdate
from app.services.monitor import check_watch

router = APIRouter(prefix="/watches", tags=["watches"])


def _get_owned_watch(db: Session, user: User, watch_id: int) -> Watch:
    """본인 소유의 감시 항목만 돌려준다. 아니면 404."""
    watch = db.get(Watch, watch_id)
    if watch is None or watch.user_id != user.id:
        raise HTTPException(status_code=404, detail="감시 항목을 찾을 수 없습니다.")
    return watch


@router.post("", response_model=WatchOut, status_code=status.HTTP_201_CREATED)
def create_watch(
    payload: WatchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    watch = Watch(
        user_id=user.id,
        query=payload.query,
        target_price=payload.target_price,
        comparison=payload.comparison,
        channel=payload.channel,
        cooldown_minutes=(
            payload.cooldown_minutes
            if payload.cooldown_minutes is not None
            else settings.default_cooldown_minutes
        ),
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


@router.get("", response_model=list[WatchOut])
def list_watches(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(
        select(Watch).where(Watch.user_id == user.id).order_by(Watch.id.desc())
    ).all()


@router.get("/{watch_id}", response_model=WatchOut)
def get_watch(
    watch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_owned_watch(db, user, watch_id)


@router.patch("/{watch_id}", response_model=WatchOut)
def update_watch(
    watch_id: int,
    payload: WatchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    watch = _get_owned_watch(db, user, watch_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(watch, field, value)
    db.commit()
    db.refresh(watch)
    return watch


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch(
    watch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    watch = _get_owned_watch(db, user, watch_id)
    db.delete(watch)
    db.commit()


@router.post("/{watch_id}/check", response_model=CheckResult)
def check_now(
    watch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """스케줄러를 기다리지 않고 지금 즉시 한 번 점검한다(데모/디버그용)."""
    watch = _get_owned_watch(db, user, watch_id)
    outcome = check_watch(db, watch)
    return CheckResult(
        checked=outcome.checked,
        current_price=outcome.current_price,
        condition_met=outcome.condition_met,
        alert=outcome.alert,
        detail=outcome.detail,
    )
