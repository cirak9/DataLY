from datetime import datetime, date

from sqlalchemy import (
    String, Text, Integer, Numeric, Date, DateTime, ForeignKey, CheckConstraint, Computed, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.catalog import Category  # noqa: F401 — لازم للـrelationship("Category") تحت


class Invoice(Base):
    """
    فاتورة مورد — بديل مجلد data/<store_id>/ + invoice.xlsx الخام. الملف الخام نفسه
    يُحفظ كـraw_file_path (تخزين، للأرشيف/إعادة المعالجة)، مو مصدر الحقيقة — القراءة
    الفعلية تصير من invoice_items بعد المعالجة.
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    supplier_name_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 1 = طريقة يدوية (بدون مخزون مورد)، 2 = إثراء من مخزون مورد، 3 = صور OCR (Claude Vision)
    method: Mapped[int] = mapped_column(Integer, nullable=False)

    # uploaded -> cleaned -> session_pending -> session_complete -> reconciled -> merged -> exported
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")

    raw_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (CheckConstraint("method IN (1, 2, 3)", name="ck_invoice_method"),)

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.item_order"
    )


class InvoiceItem(Base):
    """
    سطر صنف بالفاتورة — بديل invoice_data.xlsx. قواعد عمل مهمة محفوظة من الكود الأصلي:
    - quantity_pieces دايماً عدد قطع مفردة، أبداً عدد صناديق (قرار عمل صريح من صاحب
      المشروع، راجع session/session_generator.py الحالي).
    - per_box (عدد القطع بالصندوق) NULL صراحة لو غير معروف من الفاتورة — ممنوع نرجّع
      له قيمة افتراضية 1 ملفّقة (كسرنا هذا البق فعلياً هالجلسة: NaN/None صايرة truthy
      بايثون، فأي "or 1" ساذج يخفي القيمة الحقيقية الفاضية).
    - box_count عمود محسوب تلقائياً بقاعدة البيانات نفسها (GENERATED)، مو بكود بايثون —
      يضمن التناسق حتى لو حد حدّث الصف مباشرة بالـSQL.
    """

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)

    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    category: Mapped["Category"] = relationship(lazy="joined")

    unit_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity_pieces: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    per_box: Mapped[int | None] = mapped_column(Integer, nullable=True)
    box_count: Mapped[float | None] = mapped_column(
        Numeric(12, 4),
        Computed(
            "CASE WHEN per_box IS NOT NULL AND per_box > 0 "
            "THEN quantity_pieces / per_box ELSE NULL END",
            persisted=True,
        ),
    )

    unit_cost: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    total_price: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_item_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
