from datetime import datetime

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.invoice import InvoiceItem  # noqa: F401 — لازم للـrelationship تحت


class ReconciliationMatch(Base):
    """
    سجل دائم لكل تطابق مُقترَح واحتاج قرار بشري — بديل قائمة pending_matches المؤقتة
    (كانت تعيش بالذاكرة بس وقت تشغيلة fusion/reconciliation.py، تختفي بعدها).

    القاعدة المحفوظة من الكود الأصلي (ARCHITECTURE.md + fusion/reconciliation.py):
    ولا تطابق يُطبَّق تلقائياً إطلاقاً، مهما كانت نسبة التشابه — decision يبقى 'pending'
    لحد ما مستخدم يقرر صراحة (accept/reject/manual). match_method يميّز:
    - 'barcode': الباركود موجود بفهرس معروف (product_catalog أو مخزون المتجر السابق)
      — مسار الثقة الأعلى.
    - 'fuzzy_name': ما فيه باركود بالفاتورة أصلاً، تطابق بالاسم التقريبي (rapidfuzz
      WRatio) فقط — يحتاج حد ثقة أعلى من حالة الباركود (ما فيه مرساة هوية فيزيائية).
    warning_reason يعرض تحذير (مو رفض تلقائي) لو الاسمين مختلفين كثير نصياً أو
    الحجم/الوزن المستخرج من الاسمين متعارض — نفس فحص _size_conflict_reason() الحالي.
    """

    __tablename__ = "reconciliation_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_item_id: Mapped[int] = mapped_column(ForeignKey("invoice_items.id"), nullable=False, index=True)

    match_method: Mapped[str] = mapped_column(String(32), nullable=False)  # barcode | fuzzy_name
    matched_barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggested_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    warning_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|approved|rejected|manual
    manual_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invoice_item: Mapped["InvoiceItem"] = relationship(lazy="joined")

    @property
    def item_name(self) -> str:
        return self.invoice_item.item_name
