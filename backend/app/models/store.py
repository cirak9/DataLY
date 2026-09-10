from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Store(Base):
    """
    متجر — بديل هيكلية data/<store_id>/ الحالية (مجلدات على القرص). كل الجداول
    الثانية (invoices، inventory_lots، ...) ترتبط بـstore_id بدل مسار مجلد.

    owner_id هو حد العزل بين العملاء: كل متجر مملوك لمستخدم واحد، وكل نقاط الـAPI
    المتفرعة من store_id (فواتير، جلسات، تسويات، مخزون، تصدير) تتحقق من الملكية عبر
    هذا العمود قبل أي قراءة أو تعديل — راجع app/api/deps.py (get_owned_store وما شابه).
    """

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Supplier(Base):
    """
    مورد — بديل حقل "المورد" النصي الحر الحالي (extract_supplier_name() بملف
    excel_extractor.py كان يستخرجه كنص بس، بدون أي كيان مستقل).
    """

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
