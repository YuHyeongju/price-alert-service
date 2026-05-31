"""비밀번호 해싱 + JWT 토큰 발급/검증.

비밀번호 해시는 pbkdf2_sha256(순수 파이썬)을 사용한다.
bcrypt 같은 네이티브 빌드가 필요 없어 OS 상관없이 잘 돌아간다.
"""
from datetime import timedelta

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.utils import utcnow

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    expire = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> str | None:
    """유효하면 sub(사용자 id 문자열)를 반환, 아니면 None."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
