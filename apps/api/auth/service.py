import base64
import binascii
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

import jwt
from jwt import InvalidTokenError


class AuthenticationError(ValueError):
    pass


class AdminAuthenticationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    kind: str
    user_id: UUID | None = None
    email: str | None = None
    role: str = "guest"

    @property
    def is_registered(self) -> bool:
        return self.user_id is not None


class JwtAuthenticator:
    def __init__(self, *, secret: str, issuer: str, audience: str) -> None:
        self._secret = secret
        self._issuer = issuer or None
        self._audience = audience or None

    def authenticate(self, authorization: str | None) -> AuthIdentity:
        if not authorization:
            return AuthIdentity(kind="guest")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Authorization header must use Bearer token")
        if not self._secret:
            raise AuthenticationError("JWT verification is not configured")
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": ["sub", "exp"],
                    "verify_aud": self._audience is not None,
                    "verify_iss": self._issuer is not None,
                },
            )
            user_id = UUID(str(claims["sub"]))
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("JWT is invalid or expired") from exc
        email = claims.get("email")
        role = str(claims.get("role") or "authenticated")[:40]
        return AuthIdentity(
            kind="registered",
            user_id=user_id,
            email=str(email)[:320] if email else None,
            role=role,
        )


_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 600_000


def hash_admin_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Administrator password must contain at least 12 characters")
    resolved_salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt,
        _PASSWORD_ITERATIONS,
    )
    encoded_salt = base64.urlsafe_b64encode(resolved_salt).decode("ascii").rstrip("=")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_admin_password(password: str, encoded: str) -> bool:
    try:
        scheme, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if scheme != _PASSWORD_SCHEME:
            return False
        iterations = int(raw_iterations)
        if iterations < 100_000 or iterations > 1_000_000:
            return False
        salt = base64.urlsafe_b64decode(_restore_padding(raw_salt))
        expected = base64.urlsafe_b64decode(_restore_padding(raw_digest))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    except (binascii.Error, ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_admin_session(
    *,
    submitted_username: str,
    submitted_password: str,
    configured_username: str,
    configured_password_hash: str,
    jwt_secret: str,
    issuer: str,
    audience: str,
    lifetime_hours: int,
) -> tuple[str, datetime, AuthIdentity]:
    username_matches = hmac.compare_digest(
        submitted_username.strip().casefold().encode(),
        configured_username.strip().casefold().encode(),
    )
    password_matches = verify_admin_password(submitted_password, configured_password_hash)
    if not username_matches or not password_matches:
        raise AdminAuthenticationError("Invalid administrator credentials")
    if len(jwt_secret) < 32:
        raise AdminAuthenticationError("JWT signing is not configured")

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=lifetime_hours)
    user_id = uuid5(NAMESPACE_URL, f"automind:admin:{configured_username.casefold()}")
    claims: dict[str, object] = {
        "sub": str(user_id),
        "email": configured_username,
        "role": "admin",
        "iat": now,
        "exp": expires_at,
    }
    if issuer:
        claims["iss"] = issuer
    if audience:
        claims["aud"] = audience
    token = jwt.encode(claims, jwt_secret, algorithm="HS256")
    return (
        token,
        expires_at,
        AuthIdentity(
            kind="registered",
            user_id=user_id,
            email=configured_username,
            role="admin",
        ),
    )


def _restore_padding(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def require_registered(identity: AuthIdentity) -> UUID:
    if identity.user_id is None:
        raise AuthenticationError("Registered account is required")
    return identity.user_id
