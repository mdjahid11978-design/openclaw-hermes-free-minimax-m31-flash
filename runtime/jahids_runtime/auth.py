"""Single-owner bearer authentication for the local JAHIDS runtime.

This deliberately avoids a home-grown login, password store, or token-issuing endpoint.
Use a randomly generated API secret from a local secret manager or a mode-0600 .env file.
"""
import hmac
import os

MIN_TOKEN_LENGTH = 32
PLACEHOLDER_VALUES = {
    "",
    "replace-with-a-long-random-secret",
    "changeme",
    "your-token-here",
}

class AuthenticationConfigurationError(RuntimeError):
    """Raised when the owner credential is missing or unsafe."""

class OwnerAuthenticator:
    def __init__(self, token: str):
        if not isinstance(token, str) or token in PLACEHOLDER_VALUES or len(token) < MIN_TOKEN_LENGTH:
            raise AuthenticationConfigurationError(
                "JAHIDS_API_TOKEN must be a randomly generated secret of at least 32 characters"
            )
        self._expected_header = "Bearer " + token

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get("JAHIDS_API_TOKEN", ""))

    def authenticate(self, authorization_header: str | None) -> bool:
        supplied = authorization_header if isinstance(authorization_header, str) else ""
        return hmac.compare_digest(supplied, self._expected_header)
