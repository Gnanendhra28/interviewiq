from enum import Enum
from pydantic import BaseModel


class UserRole(str, Enum):
    CANDIDATE = "CANDIDATE"
    RECRUITER = "RECRUITER"
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


class UserDomainEntity(BaseModel):
    id: str
    email: str
    role: UserRole
    organization_id: str
    is_active: bool = True
