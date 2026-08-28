import pytest


@pytest.mark.asyncio
async def test_identity_domain_entity():
    from apps.api.app.modules.identity.domain.models import UserDomainEntity, UserRole
    user = UserDomainEntity(
        id="usr_123",
        email="test@interviewiq.ai",
        role=UserRole.CANDIDATE,
        organization_id="org_123"
    )
    assert user.email == "test@interviewiq.ai"
    assert user.role == UserRole.CANDIDATE
