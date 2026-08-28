import uuid
from typing import AsyncGenerator, Callable, Optional

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext, AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.identity.infrastructure.repositories import UserRepository
from apps.api.app.modules.identity.infrastructure.token_service import TokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an async SQLAlchemy database session context."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserORM:
    """Validates JWT access token and loads current active user."""
    if not token:
        raise DomainException("Authentication credentials were not provided", code="AUTH_REQUIRED")

    payload = TokenService.decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise DomainException("Invalid token payload", code="AUTH_INVALID_TOKEN")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id_str))
    if not user:
        raise DomainException("User associated with token not found", code="AUTH_USER_NOT_FOUND")

    if user.account_status in ("SUSPENDED", "DISABLED"):
        raise DomainException("User account is suspended or disabled", code="AUTH_ACCOUNT_SUSPENDED")

    return user


async def get_active_org_context(
    user: UserORM = Depends(get_current_user),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationContext:
    """Builds server-derived AuthorizationContext for requested X-Organization-ID."""
    requested_org_id = uuid.UUID(x_organization_id) if x_organization_id else None
    auth_service = AuthorizationService(db)
    return await auth_service.resolve_authorization_context(user, requested_org_id)


def require_permission(permission_name: str) -> Callable:
    """Dependency factory enforcing granular organization permission."""
    async def permission_checker(ctx: AuthorizationContext = Depends(get_active_org_context)) -> AuthorizationContext:
        if not ctx.has_permission(permission_name):
            raise DomainException(
                f"Permission '{permission_name}' is required to perform this action",
                code="AUTH_PERMISSION_DENIED"
            )
        return ctx

    return permission_checker


async def require_candidate_access(
    ctx: AuthorizationContext = Depends(get_active_org_context)
) -> AuthorizationContext:
    """Validates that user has a valid candidate profile within target organization boundary."""
    if not ctx.candidate_profile and not ctx.user.is_super_admin:
        raise DomainException(
            "Candidate access is required for this resource",
            code="AUTH_CANDIDATE_ACCESS_DENIED"
        )
    return ctx
