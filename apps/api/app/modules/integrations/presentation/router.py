import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.integrations.infrastructure.orm import IntegrationORM
from apps.api.app.modules.integrations.infrastructure.providers.greenhouse import GreenhouseProvider
from apps.api.app.modules.integrations.infrastructure.providers.lever import LeverProvider
from apps.api.app.modules.integrations.infrastructure.providers.workday import WorkdayProvider

router = APIRouter(prefix="/integrations", tags=["integrations"])

PROVIDERS = {
    "greenhouse": GreenhouseProvider(),
    "lever": LeverProvider(),
    "workday": WorkdayProvider(),
}

class IntegrationCreateRequest(BaseModel):
    provider_type: str
    name: str
    config_metadata_json: Dict[str, Any]
    secret: Optional[str] = None

class IntegrationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    provider_type: str
    name: str
    status: str
    config_metadata_json: Dict[str, Any]
    created_at: str

@router.post("", response_model=IntegrationResponse)
async def create_integration(
    req: IntegrationCreateRequest,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    if req.provider_type not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider type: {req.provider_type}")

    integration = IntegrationORM(
        organization_id=auth_ctx.organization_id,
        provider_type=req.provider_type,
        name=req.name,
        status="CONFIGURING",
        config_metadata_json=req.config_metadata_json,
        encrypted_secret=req.secret,
    )
    db.add(integration)
    await db.commit()

    return IntegrationResponse(
        id=integration.id,
        organization_id=integration.organization_id,
        provider_type=integration.provider_type,
        name=integration.name,
        status=integration.status,
        config_metadata_json=integration.config_metadata_json,
        created_at=integration.created_at.isoformat()
    )

@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(IntegrationORM).where(IntegrationORM.organization_id == auth_ctx.organization_id)
    result = await db.execute(stmt)
    integrations = result.scalars().all()

    return [
        IntegrationResponse(
            id=i.id,
            organization_id=i.organization_id,
            provider_type=i.provider_type,
            name=i.name,
            status=i.status,
            config_metadata_json=i.config_metadata_json,
            created_at=i.created_at.isoformat()
        )
        for i in integrations
    ]

@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    integration = await db.get(IntegrationORM, integration_id)
    if not integration or integration.organization_id != auth_ctx.organization_id:
        raise HTTPException(status_code=404, detail="Integration not found.")

    provider = PROVIDERS.get(integration.provider_type)
    res = await provider.test_connection(integration.config_metadata_json, integration.encrypted_secret or "")
    return res

@router.post("/{integration_id}/enable")
async def enable_integration(
    integration_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    integration = await db.get(IntegrationORM, integration_id)
    if not integration or integration.organization_id != auth_ctx.organization_id:
        raise HTTPException(status_code=404, detail="Integration not found.")

    integration.status = "ACTIVE"
    await db.commit()
    return {"status": "ACTIVE", "integration_id": str(integration.id)}

@router.post("/{integration_id}/disable")
async def disable_integration(
    integration_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    integration = await db.get(IntegrationORM, integration_id)
    if not integration or integration.organization_id != auth_ctx.organization_id:
        raise HTTPException(status_code=404, detail="Integration not found.")

    integration.status = "DISABLED"
    await db.commit()
    return {"status": "DISABLED", "integration_id": str(integration.id)}
