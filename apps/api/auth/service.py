from dataclasses import dataclass
from uuid import UUID

import jwt
from jwt import InvalidTokenError


class AuthenticationError(ValueError):
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


def require_registered(identity: AuthIdentity) -> UUID:
    if identity.user_id is None:
        raise AuthenticationError("Registered account is required")
    return identity.user_id
