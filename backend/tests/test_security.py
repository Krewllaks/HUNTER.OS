"""
HUNTER.OS - Security & JWT Tests
AAA Pattern | Happy Path + Edge Cases + Error Scenarios
"""
import pytest
from datetime import timedelta, datetime, timezone
from jose import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.core.config import settings


class TestPasswordHashing:
    """Unit tests for bcrypt password hashing — the tuğla (brick) layer."""

    def test_hash_returns_bcrypt_format(self):
        """Hash should start with $2b$ (bcrypt identifier)."""
        # ARRANGE
        password = "securePass123!"

        # ACT
        hashed = hash_password(password)

        # ASSERT
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt always produces 60 chars

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (salt)."""
        # ARRANGE
        password = "samePassword"

        # ACT
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # ASSERT
        assert hash1 != hash2  # Different salts → different hashes

    def test_verify_correct_password(self):
        """Correct password should verify True."""
        # ARRANGE
        password = "mySecretPass"
        hashed = hash_password(password)

        # ACT
        result = verify_password(password, hashed)

        # ASSERT
        assert result is True

    def test_verify_wrong_password(self):
        """Wrong password should verify False."""
        # ARRANGE
        hashed = hash_password("correctPassword")

        # ACT
        result = verify_password("wrongPassword", hashed)

        # ASSERT
        assert result is False

    # ── Edge Cases ──────────────────────────────────────
    def test_empty_password(self):
        """Empty string password should still hash and verify."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_unicode_password(self):
        """Turkish characters in password should work."""
        password = "şifreMçokGüçlü123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_very_long_password(self):
        """Bcrypt truncates at 72 bytes — verify behavior."""
        long_pass = "A" * 100
        hashed = hash_password(long_pass)
        assert verify_password(long_pass, hashed) is True

    def test_verify_with_invalid_hash_returns_false(self):
        """Invalid hash string should return False, not crash."""
        result = verify_password("test", "not-a-valid-hash")
        assert result is False

    def test_verify_with_empty_hash_returns_false(self):
        """Empty hash string should return False, not crash."""
        result = verify_password("test", "")
        assert result is False


class TestJWTToken:
    """Unit tests for JWT token creation and decoding."""

    def test_create_token_returns_string(self):
        """Token should be a non-empty string."""
        # ARRANGE & ACT
        token = create_access_token(subject="123")

        # ASSERT
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_subject(self):
        """Token payload should contain the subject."""
        # ARRANGE
        user_id = "42"

        # ACT
        token = create_access_token(subject=user_id)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # ASSERT
        assert payload["sub"] == "42"

    def test_token_contains_expiration(self):
        """Token should have an exp claim."""
        token = create_access_token(subject="1")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_custom_expiration(self):
        """Custom expiration delta should be respected."""
        # ARRANGE
        delta = timedelta(hours=2)

        # ACT
        token = create_access_token(subject="1", expires_delta=delta)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # ASSERT
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp_time - now
        assert 7100 < diff.total_seconds() < 7300  # ~2 hours

    def test_decode_valid_token(self):
        """Valid token should decode without error."""
        token = create_access_token(subject="99")
        payload = decode_token(token)
        assert payload["sub"] == "99"

    # ── Error Scenarios ─────────────────────────────────
    def test_decode_invalid_token_raises_401(self):
        """Invalid token string should raise HTTP 401."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_decode_expired_token_raises_401(self):
        """Expired token should raise HTTP 401."""
        from fastapi import HTTPException
        token = create_access_token(subject="1", expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_token_wrong_secret_raises_401(self):
        """Token signed with different secret should fail."""
        from fastapi import HTTPException
        token = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_integer_subject_converted_to_string(self):
        """Integer subject should be stored as string in token."""
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert isinstance(payload["sub"], str)
