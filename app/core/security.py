import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: uuid.UUID,
    *,
    name: str | None = None,
    email: str | None = None,
    image: str | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if name is not None:
        payload["name"] = name
    if email is not None:
        payload["email"] = email
    if image is not None:
        payload["image"] = image
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def _get_encryption_key() -> bytes:
    if not settings.ENCRYPTION_SECRET:
        raise ValueError("ENCRYPTION_SECRET is not set")
    try:
        key = bytes.fromhex(settings.ENCRYPTION_SECRET)
    except ValueError:
        raise ValueError("ENCRYPTION_SECRET must be a valid hex string")
    
    if len(key) not in (16, 24, 32):
        raise ValueError("ENCRYPTION_SECRET must be 16, 24, or 32 bytes long (32, 48, or 64 hex chars)")
    return key


def encrypt_data(plaintext: str) -> str:
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return (nonce + ciphertext).hex()


def decrypt_data(ciphertext_hex: str) -> str:
    try:
        key = _get_encryption_key()
        data = bytes.fromhex(ciphertext_hex)
        if len(data) < 12:
            return ""
        
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        # Catch InvalidTag, ValueError from hex parsing, etc.
        # Defensibility requirement: Fail safely if decryption fails, do not crash or leak
        return ""


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time comparison of two strings."""
    return secrets.compare_digest(a, b)
