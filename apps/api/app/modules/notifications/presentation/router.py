import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.notifications.infrastructure.orm import (
    NotificationDeliveryORM,
    NotificationPreferenceORM,
)

router = APIRouter(prefix="", tags=["notifications"])

class NotificationPreferenceRequest(BaseModel):
    channel: str # IN_APP, EMAIL, SLACK, TEAMS
    enabled_events_json: Dict[str, Any]
    webhook_url: Optional[str] = None

class NotificationDeliveryResponse(BaseModel):
    id: uuid.UUID
    channel: str
    event_type: str
    title: str
    message: str
    is_read: bool
    resource_id: Optional[str]
    created_at: str

@router.get("/notifications", response_model=List[NotificationDeliveryResponse])
async def list_notifications(
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(NotificationDeliveryORM)
        .where(NotificationDeliveryORM.organization_id == auth_ctx.active_membership.organization_id)
        .where(NotificationDeliveryORM.user_id == auth_ctx.user.id)
        .order_by(NotificationDeliveryORM.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return [
        NotificationDeliveryResponse(
            id=n.id,
            channel=n.channel,
            event_type=n.event_type,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            resource_id=n.resource_id,
            created_at=n.created_at.isoformat()
        )
        for n in notifications
    ]

@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    delivery = await db.get(NotificationDeliveryORM, notification_id)
    if not delivery or delivery.user_id != auth_ctx.user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")

    delivery.is_read = True
    await db.commit()
    return {"status": "READ", "notification_id": str(delivery.id)}

@router.get("/notification-preferences")
async def get_notification_preferences(
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(NotificationPreferenceORM)
        .where(NotificationPreferenceORM.organization_id == auth_ctx.active_membership.organization_id)
        .where(NotificationPreferenceORM.user_id == auth_ctx.user.id)
    )
    result = await db.execute(stmt)
    prefs = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "channel": p.channel,
            "enabled_events_json": p.enabled_events_json,
            "webhook_url": p.webhook_url
        }
        for p in prefs
    ]

@router.post("/notification-preferences")
async def save_notification_preference(
    req: NotificationPreferenceRequest,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(NotificationPreferenceORM)
        .where(NotificationPreferenceORM.organization_id == auth_ctx.active_membership.organization_id)
        .where(NotificationPreferenceORM.user_id == auth_ctx.user.id)
        .where(NotificationPreferenceORM.channel == req.channel)
    )
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    if pref:
        pref.enabled_events_json = req.enabled_events_json
        pref.webhook_url = req.webhook_url
    else:
        pref = NotificationPreferenceORM(
            organization_id=auth_ctx.active_membership.organization_id,
            user_id=auth_ctx.user.id,
            channel=req.channel,
            enabled_events_json=req.enabled_events_json,
            webhook_url=req.webhook_url
        )
        db.add(pref)

    await db.commit()
    return {"status": "SAVED", "channel": req.channel}
