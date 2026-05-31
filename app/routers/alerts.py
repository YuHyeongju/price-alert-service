"""알림(Alert) 조회 / 삭제 라우터."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Alert, User
from app.schemas import AlertOut

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(
        select(Alert)
        .where(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    ).all()


@router.delete("/alerts", status_code=status.HTTP_204_NO_CONTENT)
def clear_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """내 알림 전체 삭제."""
    db.execute(delete(Alert).where(Alert.user_id == user.id))
    db.commit()


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """알림 한 건 삭제(본인 소유만)."""
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    db.delete(alert)
    db.commit()
