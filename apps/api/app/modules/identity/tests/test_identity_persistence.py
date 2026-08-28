import uuid

import pytest

from apps.api.app.modules.identity.infrastructure.orm import (
    PasswordCredentialORM,
    UserORM,
)


@pytest.mark.asyncio
async def test_user_orm_creation():
    user = UserORM(
        email="john.doe@example.com",
        account_status="ACTIVE",
        is_super_admin=False
    )
    assert user.email == "john.doe@example.com"
    assert user.account_status == "ACTIVE"
    assert user.is_super_admin is False


@pytest.mark.asyncio
async def test_password_credential_orm():
    user_id = uuid.uuid4()
    cred = PasswordCredentialORM(
        user_id=user_id,
        password_hash="$2b$12$hashed_value_for_testing",
        password_algo="bcrypt"
    )
    assert cred.user_id == user_id
    assert cred.password_algo == "bcrypt"
