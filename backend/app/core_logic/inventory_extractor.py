# منقول شبه حرفي من extractors/inventory_extractor.py بالأداة الأصلية (CLI) —
# detect_inventory_columns() بنفس منطق كشف الأعمدة الذكي (تطابق دقيق أولاً، ثم
# احتواء جزئي لأي عمود ناقص). إضافة عن الأصلي: كشف اختياري لعمودي الكمية وتكلفة
# الوحدة — old_inventory.xlsx الأصلي ما كان يتتبعهم (barcode/name/expiration بس)،
# لكن inventory_lots بالتطبيق الجديد يحتاجهم لتحديث مخزون فعلي، فلو موجودين بالملف
# نستخدمهم، ولو لأ يبقون فاضين (NULL) بدل تخمين قيمة.
import pandas as pd

from app.core_logic._logger import get_logger

log = get_logger()

INVENTORY_POSSIBLE_COLUMNS = {
    "barcode": [
        "باركود", "الباركود", "كود", "الكود", "كود الصنف", "رمز", "الرمز",
        "code", "barcode", "bar code", "sku", "item code",
    ],
    "name": [
        "اسم الصنف", "الاسم", "اسم المنتج", "الصنف", "الوصف", "وصف الصنف",
        "name", "product_name", "product name", "item name", "description", "descr",
    ],
    "expiration": [
        "صلاحية", "الصلاحية", "انتهاء", "تاريخ الانتهاء", "تاريخ الصلاحية",
        "expiration", "expiry", "exp date", "exp. date", "date_xp",
    ],
    "quantity": [
        "الكمية", "كمية", "العدد", "qty", "quantity", "الكمية المتوفرة", "المتوفر",
    ],
    "unit_cost": [
        "سعر التكلفة", "تكلفة الوحدة", "سعر الوحدة", "التكلفة", "cost", "unit cost", "unit_cost",
    ],
}


class InventoryImportError(Exception):
    """
    يُرفع لما ملف مخزون قديم موجود فعلاً بس فشلت قراءته (أعمدة ناقصة، صيغة تالفة) —
    أبداً ما نكمل بافتراض "ملف فاضي" بهالحالة (عكس ملف غير موجود إطلاقاً، اللي يعني
    فعلاً "أول مخزون للمتجر") — بديل InventoryLoadError بالأداة الأصلية، نفس الفلسفة:
    فشل قراءة حقيقي يوقف العملية بدل ما يمسح تاريخ المخزون بصمت.
    """
    pass


def _find_inventory_column(columns: list[str], hints: list[str], exact: bool) -> str | None:
    for col in columns:
        col_lower = col.strip().lower()
        for h in hints:
            if (col_lower == h) if exact else (h in col_lower):
                return col
    return None


def detect_inventory_columns(df: pd.DataFrame) -> tuple[str, str, str, str | None, str | None]:
    """يرجّع (عمود الباركود، الاسم، الصلاحية، الكمية أو None، تكلفة الوحدة أو None) —
    الثلاثة الأول إجباريون (يرفع ValueError لو ناقص أي وحد)، الأخيرين اختياريون."""
    columns = [str(col).strip() for col in df.columns]

    barcode_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS["barcode"], exact=True)
    name_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS["name"], exact=True)
    expiration_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS["expiration"], exact=True)

    remaining = [c for c in columns if c not in (barcode_col, name_col, expiration_col)]
    if barcode_col is None:
        barcode_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["barcode"], exact=False)
        remaining = [c for c in remaining if c != barcode_col]
    if name_col is None:
        name_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["name"], exact=False)
        remaining = [c for c in remaining if c != name_col]
    if expiration_col is None:
        expiration_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["expiration"], exact=False)
        remaining = [c for c in remaining if c != expiration_col]

    if not barcode_col or not name_col or not expiration_col:
        missing = []
        if not barcode_col:
            missing.append("الباركود")
        if not name_col:
            missing.append("اسم الصنف")
        if not expiration_col:
            missing.append("الصلاحية")
        raise ValueError(f"الأعمدة المطلوبة غير موجودة: {', '.join(missing)}")

    quantity_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["quantity"], exact=True) \
        or _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["quantity"], exact=False)
    remaining = [c for c in remaining if c != quantity_col]
    unit_cost_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["unit_cost"], exact=True) \
        or _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS["unit_cost"], exact=False)

    return barcode_col, name_col, expiration_col, quantity_col, unit_cost_col


def _to_float_or_none(value) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_barcode_str(value) -> str:
    """باركودات رقمية بعمود فيه أي خلية فاضية تصير float64 بـpandas تلقائياً
    (123 → 123.0) — بدون هالتحويل، أي باركود رقمي بالملف يطلع بلاحقة '.0' زايدة
    ما تطابق الباركود الحقيقي بأي مكان ثاني بالنظام (تسوية، مخزون، ...)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _to_date_str_or_none(value) -> str | None:
    """يرجّع 'YYYY-MM-DD' أو None — يقبل Timestamp/datetime أو نص، بدون تخمين لو غير مفهوم."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nat" or text.lower() == "nan":
        return None
    try:
        return pd.to_datetime(text).date().isoformat()
    except (ValueError, TypeError):
        return None


def extract_old_inventory(file_path_or_buffer) -> list[dict]:
    """
    يقرأ ملف مخزون قديم (باركود/اسم/صلاحية إجباري، كمية/تكلفة وحدة اختياري لو موجودين)
    ويرجّع صفوف نظيفة جاهزة للـupsert — بديل extract_old_inventory بالأداة الأصلية.
    يرفع InventoryImportError صراحة لو فشلت القراءة أو الأعمدة المطلوبة ناقصة، بدل
    ما يرجّع قائمة فاضية (فشل حقيقي غير "مافيش ملف").
    """
    try:
        df = pd.read_excel(file_path_or_buffer)
    except Exception as e:
        raise InventoryImportError(f"تعذّرت قراءة الملف — تأكد إنه ملف إكسل سليم وغير مفتوح ببرنامج آخر: {e}") from e

    if df.empty:
        return []

    try:
        barcode_col, name_col, expiration_col, quantity_col, unit_cost_col = detect_inventory_columns(df)
    except ValueError as e:
        raise InventoryImportError(str(e)) from e

    rows: list[dict] = []
    for _, row in df.iterrows():
        barcode = _to_barcode_str(row[barcode_col])
        if not barcode or barcode.lower() == "nan":
            continue
        rows.append({
            "barcode": barcode,
            "item_name": str(row[name_col]).strip() or None,
            "expiration_date": _to_date_str_or_none(row[expiration_col]),
            "quantity": _to_float_or_none(row[quantity_col]) if quantity_col else None,
            "unit_cost": _to_float_or_none(row[unit_cost_col]) if unit_cost_col else None,
        })

    return rows
