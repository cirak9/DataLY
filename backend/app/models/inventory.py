from datetime import datetime, date

from sqlalchemy import String, Text, Numeric, Date, DateTime, ForeignKey, Index, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.invoice import InvoiceItem  # noqa: F401 — لازم للـrelationship تحت


class InventoryLot(Base):
    """
    دفعة/لوت مخزون تراكمي للمتجر — بديل old_inventory.xlsx. **فريد بالـ(متجر، باركود،
    صلاحية) مو بالباركود لحاله** — نفس صنف بصلاحيات مختلفة (دفعات وصول مختلفة) يبقى
    صفوف منفصلة عمداً، مطابق تماماً لقاعدة fusion/inventory_manager.py update_inventory()
    الحالية (drop_duplicates(subset=['barcode','expiration'], keep='last')).
    """

    __tablename__ = "inventory_lots"
    __table_args__ = (
        Index(
            "ux_inventory_lot",
            "store_id",
            "barcode",
            text("COALESCE(expiration_date, DATE '9999-12-31')"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(64), nullable=False)
    item_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    last_invoice_item_id: Mapped[int | None] = mapped_column(ForeignKey("invoice_items.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    last_invoice_item: Mapped["InvoiceItem | None"] = relationship(lazy="joined")

    @property
    def category(self):
        """
        تصنيف اللوت مُشتق من آخر صنف فاتورة حدّثه — لا عمود category_id مباشر بهالجدول
        (اللوت بديل old_inventory.xlsx المسطّح أصلاً). يتيح فلترة شاشة المخزون بالتصنيف
        بدون تكرار بيانات التصنيف بكل لوت.
        """
        return self.last_invoice_item.category if self.last_invoice_item else None
