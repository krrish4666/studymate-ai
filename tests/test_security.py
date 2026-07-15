import uuid

import pytest
from passlib.context import CryptContext

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    encrypt_data,
    decrypt_data,
)


class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        hashed = hash_password("securePass123")
        assert isinstance(hashed, str)
        assert hashed != "securePass123"

    def test_hash_password_different_each_time(self):
        h1 = hash_password("securePass123")
        h2 = hash_password("securePass123")
        assert h1 != h2

    def test_verify_password_correct(self):
        hashed = hash_password("securePass123")
        assert verify_password("securePass123", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("securePass123")
        assert verify_password("wrongPassword", hashed) is False

    def test_hash_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestJWT:
    def test_create_access_token_returns_string(self):
        uid = uuid.uuid4()
        token = create_access_token(uid)
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_valid_token(self):
        uid = uuid.uuid4()
        token = create_access_token(uid)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(uid)

    def test_decode_invalid_token(self):
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self):
        uid = uuid.uuid4()
        from jose import jwt
        from datetime import datetime, timedelta, timezone
        expired = jwt.encode(
            {
                "sub": str(uid),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            },
            "test-secret",
            algorithm="HS256",
        )
        result = decode_access_token(expired)
        assert result is None


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "sk-test-api-key-12345"
        encrypted = encrypt_data(original)
        assert encrypted != original
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_encrypt_different_each_time(self):
        data = "same-data"
        e1 = encrypt_data(data)
        e2 = encrypt_data(data)
        assert e1 != e2

    def test_decrypt_tampered_data_raises(self):
        data = "valid-data"
        encrypted = encrypt_data(data)
        tampered = "ff" + encrypted[2:]
        with pytest.raises(Exception):
            decrypt_data(tampered)
