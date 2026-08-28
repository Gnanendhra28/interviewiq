from passlib.context import CryptContext
from apps.api.app.core.logging import logger

try:
    pwd_context = CryptContext(
        schemes=["argon2", "bcrypt"],
        deprecated="auto",
        argon2__memory_cost=65536,
        argon2__time_cost=3,
        argon2__parallelism=4,
    )
    pwd_context.hash("test_init", scheme="argon2")
except Exception as e:
    logger.warning(f"Argon2 backend initialization failed ({e}). Falling back to Bcrypt scheme.")
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
    )


class PasswordHasher:
    """Production Password Hasher supporting Argon2id with Bcrypt fallback."""

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        try:
            return pwd_context.needs_update(hashed_password)
        except Exception:
            return False
