import base64
import hashlib
import secrets

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        # Dev-only deterministic fallback. README warns; prod MUST set ENCRYPTION_KEY.
        digest = hashlib.sha256(b"dev-insecure-encryption-key").digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def generate_token() -> str:
    return secrets.token_urlsafe(32)
