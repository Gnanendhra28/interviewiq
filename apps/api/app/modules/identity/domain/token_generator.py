import hashlib
import secrets


def generate_opaque_token(length_bytes: int = 32) -> str:
    """Generates a cryptographically random, URL-safe opaque token string."""
    return secrets.token_urlsafe(length_bytes)


def hash_token(token: str) -> str:
    """Computes SHA-256 hash of a raw token for safe database persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
