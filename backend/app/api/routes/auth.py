from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.store import Store
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.email == payload.identifier) | (User.phone_number == payload.identifier))
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بيانات الدخول غلط")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    تسجيل ذاتي لتاجر جديد — رقم هاتف بدل بريد إلكتروني، ومتجر يُنشأ تلقائياً بنفس
    اللحظة (مملوك للحساب الجديد مباشرة). يرجّع توكن جاهز — دخول تلقائي بعد التسجيل
    مباشرة، بدون خطوة تسجيل دخول منفصلة.
    """
    if db.query(User).filter(User.phone_number == payload.phone_number).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رقم الهاتف مسجّل مسبقاً")

    user = User(phone_number=payload.phone_number, hashed_password=hash_password(payload.password))
    db.add(user)
    db.flush()  # يحتاج user.id قبل إنشاء المتجر، بدون commit كامل بعد

    # code فريد إجبارياً بجدول stores — رقم الهاتف فريد أصلاً (اتصيد فوق لو مكرر)، فمناسب كأساس.
    store = Store(name=payload.store_name, code=f"store_{payload.phone_number}", owner_id=user.id)
    db.add(store)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
