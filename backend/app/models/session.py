from datetime import datetime, date

from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.invoice import Invoice, InvoiceItem  # noqa: F401 — لازم للـrelationship تحت


class IntakeSession(Base):
    """
    جلسة استلام التاجر — بديل session_template.xlsx/session_output.xlsx وواجهة
    streamlit الحالية (session/receiving_app.py). كل فاتورة لها جلسة واحدة بالضبط.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), unique=True, nullable=False)
    method: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending|complete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["SessionItem"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionItem.id"
    )
    invoice: Mapped["Invoice"] = relationship(lazy="joined")


class SessionItem(Base):
    """
    صف تعبئة صنف واحد بالجلسة — بديل عمود الباركود/الصلاحية/سعر البيع بـ
    session_output.xlsx. بالطريقة الثانية، الباركود/الصلاحية يجون معبّئين مسبقاً
    (إثراء من مخزون المورد) والتاجر يعبّي السعر بس — نفس فكرة fusion/supplier_matcher.py
    enrich_invoice_from_supplier() الحالية، هون كتعبئة افتراضية بالفورم بدل ملف إكسل.
    """

    __tablename__ = "session_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    invoice_item_id: Mapped[int] = mapped_column(ForeignKey("invoice_items.id"), nullable=False, unique=True)

    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    session: Mapped["IntakeSession"] = relationship(back_populates="items")
    invoice_item: Mapped["InvoiceItem"] = relationship(lazy="joined")

    @property
    def item_name(self) -> str:
        return self.invoice_item.item_name

    @property
    def unit_cost(self) -> float | None:
        return self.invoice_item.unit_cost
