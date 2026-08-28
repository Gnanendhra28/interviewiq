import re

from apps.api.app.core.exceptions import DomainException


class PasswordPolicy:
    """Configurable password policy validator."""

    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special

    def validate(self, password: str) -> None:
        if not password or len(password) < self.min_length:
            raise DomainException(
                f"Password must be at least {self.min_length} characters long.",
                code="PASSWORD_TOO_SHORT",
            )

        if self.require_uppercase and not re.search(r"[A-Z]", password):
            raise DomainException(
                "Password must contain at least one uppercase letter.",
                code="PASSWORD_MISSING_UPPERCASE",
            )

        if self.require_lowercase and not re.search(r"[a-z]", password):
            raise DomainException(
                "Password must contain at least one lowercase letter.",
                code="PASSWORD_MISSING_LOWERCASE",
            )

        if self.require_digits and not re.search(r"\d", password):
            raise DomainException(
                "Password must contain at least one digit.",
                code="PASSWORD_MISSING_DIGIT",
            )

        if self.require_special and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
            raise DomainException(
                "Password must contain at least one special character.",
                code="PASSWORD_MISSING_SPECIAL",
            )


default_password_policy = PasswordPolicy()
