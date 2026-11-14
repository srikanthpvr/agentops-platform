"""
app/core/security.py
====================
All cryptographic primitives used by the platform:

* Password hashing  (bcrypt via passlib)
* JWT creation / decoding  (python-jose)
* API key generation and verification  (PBKDF2-sha256 via passlib)

Nothing in this module touches the database or HTTP layer directly.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256

from app.core.config import settings


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*.

    Args:
        password: Plain-text password supplied by the user.

    Returns:
        A bcrypt hash string safe to store in the database.
    """
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain-text password against a stored bcrypt hash.

    Args:
        plain:  The raw password from a login request.
        hashed: The stored hash retrieved from the database.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Encode *data* as a signed JWT access token.

    Args:
        data:          Payload to encode.  Must NOT contain sensitive secrets.
        expires_delta: Custom TTL.  Defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        A compact JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(tz=timezone.utc)
    ttl = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = now + ttl
    to_encode["iat"] = now
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token.

    Args:
        token: The raw JWT string from the ``Authorization`` header.

    Returns:
        The decoded payload dict, or ``None`` if the token is invalid /
        expired / tampered.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------

# Characters allowed in the random portion of an API key (URL-safe)
_API_KEY_ALPHABET: str = string.ascii_letters + string.digits
_API_KEY_RANDOM_LENGTH: int = 32
_API_KEY_PREFIX_CHARS: int = 12   # chars used for fast lookup by prefix


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key triple.

    The generated key has the form ``ao_live_<32 random chars>``.

    Returns:
        A 3-tuple ``(full_key, prefix, hashed_key)`` where:

        * ``full_key``   – the complete key shown to the user **once**.
        * ``prefix``     – the first 12 characters used as a lookup index.
        * ``hashed_key`` – the PBKDF2-sha256 hash stored in the database.

    Security notes:
        * ``secrets.choice`` is used for cryptographically secure randomness.
        * Only the hash is persisted; the full key is irrecoverable afterwards.
    """
    random_part = "".join(secrets.choice(_API_KEY_ALPHABET) for _ in range(_API_KEY_RANDOM_LENGTH))
    full_key = f"ao_live_{random_part}"
    prefix = full_key[:_API_KEY_PREFIX_CHARS]          # e.g. "ao_live_abcd"
    hashed_key = pbkdf2_sha256.hash(full_key)
    return full_key, prefix, hashed_key


def verify_api_key(plain_key: str, hashed: str) -> bool:
    """Verify a raw API key against its stored PBKDF2-sha256 hash.

    Args:
        plain_key: The key string presented by the caller.
        hashed:    The hash retrieved from the database via the prefix index.

    Returns:
        ``True`` if the key matches the stored hash.
    """
    return pbkdf2_sha256.verify(plain_key, hashed)
