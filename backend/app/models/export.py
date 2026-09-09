from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AlsahlExport(Base):
    """سجل كل عملية تصدير لملف السهل — بديل output/<store_id>/output_alsahl.xlsx المفرد
    (كان يُكتب فوقه بكل مرة، بدون أي أرشيف لعمليات التصدير السابقة)."""

    __tablename__ = "alsahl_exports"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
