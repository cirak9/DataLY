from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """
    حسابان: إداري (بريد إلكتروني — تسجيل يدوي عبر scripts/create_admin.py) أو تاجر
    ذاتي التسجيل (رقم هاتف — عبر POST /auth/register). واحد منهم على الأقل لازم
    يكون موجود (يتحقق منه بمنطق التسجيل، مو بقيد قاعدة بيانات). تسجيل الدخول
    (POST /auth/login) يقبل أي واحد منهم كمعرّف.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
