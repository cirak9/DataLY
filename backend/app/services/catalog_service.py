import re

from sqlalchemy.orm import Session

from app.core_logic.categorizer import get_category_by_name
from app.models.catalog import Category, CategoryKeyword, ProductCatalog

_IGNORED_SUB = ("", "أخرى", "nan", "none")


def _match_manual_keyword(db: Session, item_name: str) -> int | None:
    """
    طبقة إضافية فوق خوارزمية categorizer.py الثابتة (categories_seed.json) — كلمات
    مفتاحية يديفها المستخدم من شاشة إدارة التصنيفات، بمطابقة بسيطة (بدون fuzzy) عشان
    ما نكرر منطق الخوارزمية المضبوطة أصلاً بعناية بـcategorizer.py. تُفحص قبل التخمين
    التلقائي مباشرة — تصحيح يدوي صريح يفوز على تخمين عام، بس بعد أولوية الباركود.
    """
    text = item_name.lower()
    words = set(re.split(r"\s+|،|\.|-|/", text))
    for kw in db.query(CategoryKeyword).all():
        keyword = kw.keyword.strip().lower()
        if not keyword:
            continue
        matched = keyword in words if kw.is_whole_word else keyword in text
        if matched:
            return kw.category_id
    return None


def get_or_create_category(db: Session, main: str, sub: str) -> Category:
    """
    غالباً موجودة أصلاً (مبذورة من categories_seed.json — راجع alembic/versions/0002)
    بما إن get_category_by_name() ما ترجّع إلا (رئيسي، فرعي) من نفس الملف. get_or_create
    احتياط لو تصنيف جديد انضاف مستقبلاً بدون إعادة تشغيل الهجرة.
    """
    category = db.query(Category).filter(Category.main == main, Category.sub == sub).first()
    if category:
        return category
    category = Category(main=main, sub=sub)
    db.add(category)
    db.flush()
    return category


def get_category_id(
    db: Session,
    item_name: str,
    category_hint: str = "",
    sub_hint: str = "",
    barcode: str | None = None,
) -> int | None:
    """
    بديل utils/categorizer.py get_category() الأصلية — بس هون أولوية الباركود عبر
    product_catalog (بديل utils/barcode_categories.py، صار جدول بدل ملف JSON). ترتيب
    الأولوية: تصنيف مُعتمَد مسبقًا > الفهرس المركزي بالباركود > كلمات مفتاحية يدوية
    (شاشة إدارة التصنيفات، جدول category_keywords) > تخمين تلقائي بالاسم (الخوارزمية
    الثابتة بـcategorizer.py).
    """
    if sub_hint and sub_hint not in _IGNORED_SUB:
        return get_or_create_category(db, category_hint, sub_hint).id

    if barcode:
        entry = db.query(ProductCatalog).filter(ProductCatalog.barcode == barcode).first()
        if entry and entry.category_id:
            return entry.category_id

    manual_category_id = _match_manual_keyword(db, item_name)
    if manual_category_id:
        return manual_category_id

    main, sub = get_category_by_name(item_name, category_hint, sub_hint)
    return get_or_create_category(db, main, sub).id
