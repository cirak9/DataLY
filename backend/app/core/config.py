from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    كل الإعدادات تُقرأ من متغيرات البيئة (.env محلياً، أو env vars فعلية بالاستضافة) —
    بدون أي قيمة سرية مكتوبة بالكود مباشرة.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://dataly:dataly@localhost:5432/dataly"
    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # أسبوع — مستخدم واحد فقط، جلسة طويلة مقصودة
    cors_origins: list[str] = ["http://localhost:5173"]

    # مسار تخزين الفواتير المرفوعة وملفات التصدير — قرص محلي بالتطوير، تقدر تتحول
    # لتخزين خارجي (S3-compatible) لاحقاً بدون تغيير أي كود يستدعي storage.py
    storage_dir: str = "./storage"

    # استخراج فواتير الصور عبر Claude Vision — None لحد ما يُضاف المفتاح فعلياً بالاستضافة؛
    # ocr_service يرفض بوضوح (503) لو الخدمة استُدعيت قبل توفّر المفتاح، بدل خطأ غامض
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"


settings = Settings()
