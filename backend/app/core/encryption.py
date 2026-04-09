"""
HUNTER.OS - Credential Encryption (Fernet symmetric)
Encrypts/decrypts sensitive values stored in the database:
SMTP passwords, LinkedIn session cookies, etc.
"""
import logging
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return a cached Fernet instance, creating one if needed."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = settings.ENCRYPTION_KEY
    if not key:
        if not settings.DEBUG:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. This is required in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
                "and set it in your .env file."
            )
        # Dev-only: generate a temporary key (data lost on restart)
        key = Fernet.generate_key().decode()
        logger.warning(
            "ENCRYPTION_KEY not set — generated temporary key (DEBUG mode). "
            "Data encrypted with this key will be UNRECOVERABLE after restart."
        )
        settings.ENCRYPTION_KEY = key

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a URL-safe base64-encoded token."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext.

    Raises ValueError if the token is invalid or was encrypted with
    a different key.
    """
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt value — wrong key or corrupted data")
        raise ValueError("Decryption failed: invalid token or wrong key") from exc
