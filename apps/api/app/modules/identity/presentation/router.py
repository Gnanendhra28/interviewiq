from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.config import settings
from apps.api.app.core.dependencies import get_active_org_context, get_current_user, get_db
from apps.api.app.modules.identity.application.email_verification_use_case import (
    EmailVerificationUseCase,
)
from apps.api.app.modules.identity.application.login_use_case import LoginUseCase
from apps.api.app.modules.identity.application.logout_use_case import LogoutUseCase
from apps.api.app.modules.identity.application.password_reset_use_case import PasswordResetUseCase
from apps.api.app.modules.identity.application.refresh_token_use_case import RefreshTokenUseCase
from apps.api.app.modules.identity.application.register_use_case import RegisterUseCase
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.identity.infrastructure.repositories import SessionRepository

router = APIRouter(prefix="/auth", tags=["Identity & Access"])
org_router = APIRouter(prefix="/organizations", tags=["Organizations & Context"])


# --- Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    token: str


class RevokeSessionRequest(BaseModel):
    session_id: str


# --- Auth Endpoints ---

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    use_case = RegisterUseCase(db)
    return await use_case.execute(email=req.email, password=req.password)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    login_case = LoginUseCase(db)
    result_body, raw_refresh_token = await login_case.execute(
        email=req.email,
        password=req.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

    is_cookie_secure = getattr(settings, 'COOKIE_SECURE', False) or settings.ENVIRONMENT in ("production", "staging")
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=is_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return result_body


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = RefreshTokenUseCase(db)
    result_body, new_raw_refresh = await use_case.execute(
        raw_refresh_token=refresh_token,
        ip_address=ip_address
    )

    # Set rotated HttpOnly cookie
    is_cookie_secure = getattr(settings, 'COOKIE_SECURE', False) or settings.ENVIRONMENT in ("production", "staging")
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=is_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return result_body


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    use_case = LogoutUseCase(db)
    res = await use_case.logout_current_session(refresh_token)

    # Clear Refresh Cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return res


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    response: Response,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    use_case = LogoutUseCase(db)
    res = await use_case.logout_all_sessions(current_user.id)

    # Clear Refresh Cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return res


@router.post("/email-verification/request", status_code=status.HTTP_200_OK)
async def request_email_verification(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    use_case = EmailVerificationUseCase(db)
    return await use_case.send_verification_email(current_user.id)


@router.post("/email-verification/verify", status_code=status.HTTP_200_OK)
async def verify_email(
    req: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = EmailVerificationUseCase(db)
    return await use_case.verify_email_token(req.token)


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = PasswordResetUseCase(db)
    return await use_case.request_password_reset(req.email)


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = PasswordResetUseCase(db)
    return await use_case.confirm_password_reset(req.token, req.new_password)


# --- Session Management Endpoints ---

@router.get("/sessions", status_code=status.HTTP_200_OK)
async def list_active_sessions(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sess_repo = SessionRepository(db)
    sessions = await sess_repo.get_active_user_sessions(current_user.id)
    return [
        {
            "id": str(s.id),
            "family_id": str(s.family_id),
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "device_info": s.device_info,
            "last_refreshed_at": s.last_refreshed_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    use_case = LogoutUseCase(db)
    return await use_case.revoke_specific_session(current_user.id, session_id)


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from apps.api.app.core.authorization.context import AuthorizationService
    auth_service = AuthorizationService(db)
    ctx = await auth_service.resolve_authorization_context(current_user)

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "is_super_admin": current_user.is_super_admin,
            "account_status": current_user.account_status,
        },
        "active_organization": {
            "id": str(ctx.active_organization.id),
            "name": ctx.active_organization.name,
            "slug": ctx.active_organization.slug,
        } if ctx.active_organization else None,
        "role": {
            "id": str(ctx.role.id),
            "name": ctx.role.name,
        } if ctx.role else None,
        "permissions": list(ctx.permissions),
    }


# --- Organization & Authorization Context Endpoints ---

@org_router.get("/context", status_code=status.HTTP_200_OK)
@router.get("/org-context", status_code=status.HTTP_200_OK)
async def get_organization_context(
    ctx: AuthorizationContext = Depends(get_active_org_context)
):
    return {
        "user_id": str(ctx.user.id),
        "email": ctx.user.email,
        "is_super_admin": ctx.user.is_super_admin,
        "active_organization": {
            "id": str(ctx.active_organization.id),
            "name": ctx.active_organization.name,
            "slug": ctx.active_organization.slug,
        } if ctx.active_organization else None,
        "role": {
            "id": str(ctx.role.id),
            "name": ctx.role.name,
        } if ctx.role else None,
        "permissions": list(ctx.permissions),
        "is_candidate": ctx.candidate_profile is not None,
        "candidate_profile_id": str(ctx.candidate_profile.id) if ctx.candidate_profile else None
    }
