from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import User

# tokenUrl هون بس لتوثيق Swagger (/docs) — تسجيل الدخول الفعلي عبر /auth/login بجسم JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="غير مصرّح — سجّل الدخول من جديد",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    email = decode_access_token(token)
    if not email:
        raise unauthorized
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise unauthorized
    return user
