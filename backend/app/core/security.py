"""Password hashing and session-token primitives. man this feature is ass i hate making this one"""

import hashlib
import secrets
from functools import cache

from pwdlib import PasswordHash

# Argon2id with the library's current recommended parameters (OWASP-aligned). Hashes that were made with
# weaker parameters are transparently upgraded on the next successful login.
_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """(is_valid, upgraded_hash). ``upgraded_hash`` is set when the stored hash should be replaced."""
    return _hasher.verify_and_update(password, password_hash)


@cache
def dummy_hash() -> str:
    """Verified against when the e-mail is unknown, so "no such user" costs the same time as "wrong password"."""
    return _hasher.hash(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits of entropy


def hash_token(token: str) -> str:
    """Only this digest is stored. The token itself has enough entropy that a plain SHA-256 is sufficient."""
    return hashlib.sha256(token.encode()).hexdigest()
