from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class AuthTokenPayload(BaseModel):
    user_id: str
    organization_id: str
    role: str
    token_type: str = "access"
    jti: Optional[str] = None


class AuthenticationProvider(ABC):
    """
    Abstract Authentication Provider Interface.
    Decouples core application domain from specific authentication mechanisms
    (Local JWT + Argon2, OAuth2 / OIDC, SAML enterprise SSO).
    """

    @abstractmethod
    async def authenticate_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate user credentials and return user domain context."""
        pass

    @abstractmethod
    async def create_session_tokens(self, user_id: str, organization_id: str, role: str) -> Dict[str, str]:
        """Generate access and refresh token pair."""
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> AuthTokenPayload:
        """Verify JWT access token and return token claims."""
        pass

    @abstractmethod
    async def revoke_session(self, refresh_token: str) -> bool:
        """Revoke active refresh token and add jti to revocation store."""
        pass
