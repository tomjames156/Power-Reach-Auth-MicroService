from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
import hashlib, secrets, bcrypt
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # 1. Convert string to bytes
    password_bytes = password.encode('utf-8')

    # 2. Pre-hash with SHA-256 to ensure it's under 72 bytes
    sha256_hash = hashlib.sha256(password_bytes).digest()

    # 3. Hash with bcrypt
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(sha256_hash, salt)

    # 4. DECODE to string for storage/JSON
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password_str: str) -> bool:
    # 1. Prepare plain password
    password_bytes = plain_password.encode('utf-8')
    sha256_hash = hashlib.sha256(password_bytes).digest()

    # 2. Convert stored string back to bytes for bcrypt.checkpw
    return bcrypt.checkpw(sha256_hash, hashed_password_str.encode('utf-8'))

def create_access_token(user_id: str, user_type: str) -> str:
    payload = {
        "sub": user_id,
        "role": user_type,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, hashed_token). Store only the hash."""
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        return payload
    except JWTError:
        raise ValueError("Invalid or expired token")


def create_verification_token(user_id: str, email: str) -> str:
    """Short-lived token carrying user identity for email confirmation."""
    payload = {
        "sub": user_id,
        "email": email,
        "type": "email_verification",
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=settings.verification_token_expire_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_verification_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "email_verification":
            raise ValueError("Wrong token type")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid or expired verification token: {e}")
