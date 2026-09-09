from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Category(Base):
    """بديل utils/categories.json — تصنيف رئيسي/فرعي."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("main", "sub", name="ux_category_main_sub"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    main: Mapped[str] = mapped_column(String(100), nullable=False)
    sub: Mapped[str] = mapped_column(String(100), nullable=False)

    keywords: Mapped[list["CategoryKeyword"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class CategoryKeyword(Base):
    """
    بديل categories.json['keywords']/['whole_word_keywords'] — نفس منطق التصنيف
    (utils/categorizer.py get_category()) يُبنى فهرسه من هذا الجدول بدل تحميل JSON.
    """

    __tablename__ = "category_keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_whole_word: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    category: Mapped["Category"] = relationship(back_populates="keywords")


class ProductCatalog(Base):
    """
    فهرس منتجات مشترك بين كل المتاجر، بالباركود — بديل master_items.xlsx (كان للقراءة
    فقط، يتجدد يدوياً) + utils/barcode_categories.json (الوحيد اللي كان يتراكم تلقائياً
    فعلاً). بوجود قاعدة بيانات، لا داعي لقيد "للقراءة فقط" القديم — يتراكم ويتحسّن
    تلقائياً من كل فاتورة، بنفس انضباط "التسمية تحتاج موافقة بشرية" المحفوظ بجدول
    reconciliation_matches (التراكم الأولي غير مشروط بموافقة، إعادة التسمية لاحقاً مشروطة).
    """

    __tablename__ = "product_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    source_store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
