from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    # البريد الإلكتروني (حساب إداري) أو رقم الهاتف (حساب تاجر ذاتي التسجيل) — نفس الحقل،
    # الباك إند يجرّب الاثنين (راجع routes/auth.py).
    identifier: str
    password: str


class RegisterRequest(BaseModel):
    store_name: str
    phone_number: str
    password: str

    @field_validator("store_name", "phone_number")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الحقل مطلوب")
        return v

    @field_validator("password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("كلمة المرور لازم تكون 6 أحرف على الأقل")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str | None
    phone_number: str | None

    model_config = {"from_attributes": True}
