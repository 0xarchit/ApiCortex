"""Dashboard endpoints.

Provides aggregated metrics and summaries for monitoring and observability
across APIs and endpoints.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.api import DashboardNotificationOut, DashboardNotificationReadAllOut, DashboardSummaryOut
from app.services.dashboard_service import DashboardService


router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(request: Request, window_hours: int = 24):
    org_id = uuid.UUID(str(request.state.org_id))
    window_hours = max(1, min(window_hours, 168))
    return DashboardService.summary(org_id=org_id, window_hours=window_hours)


@router.get("/notifications", response_model=list[DashboardNotificationOut])
def list_notifications(
    request: Request,
    limit: int = 20,
    unread_only: bool = False,
    db: Session = Depends(get_db),
):
    org_id = uuid.UUID(str(request.state.org_id))
    bounded_limit = max(1, min(limit, 100))
    stmt = (
        select(Notification)
        .where(Notification.org_id == org_id)
        .order_by(Notification.created_at.desc())
        .limit(bounded_limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    rows = list(db.scalars(stmt).all())
    return rows


@router.post("/notifications/{notification_id}/read", response_model=DashboardNotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    org_id = uuid.UUID(str(request.state.org_id))
    row = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not row.is_read:
        row.is_read = True
        row.read_at = datetime.now(timezone.utc)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.post("/notifications/read-all", response_model=DashboardNotificationReadAllOut)
def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_db),
):
    org_id = uuid.UUID(str(request.state.org_id))
    now_ts = datetime.now(timezone.utc)
    unread_count = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.org_id == org_id,
            Notification.is_read.is_(False),
        )
    )
    updated_count = int(unread_count or 0)
    if updated_count > 0:
        db.execute(
            update(Notification)
            .where(
                Notification.org_id == org_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=now_ts)
        )
        db.commit()
    return DashboardNotificationReadAllOut(updated=updated_count)
