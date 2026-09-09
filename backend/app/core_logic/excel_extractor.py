# منقول شبه حرفي من extractors/excel_extractor.py بالأداة الأصلية (CLI) — راجع
# docs/REBUILD_PLAN.md قسم 2 لسبب النقل بدون تعديل منطق. التغيير الوحيد: extract_from_excel
# تقبل مسار ملف أو buffer بالذاكرة (BytesIO) بدل مسار قرص بس — pandas.read_excel يدعم
# الاثنين شفافياً، وهذا يسمح للـAPI يقرأ الملف المرفوع مباشرة من الطلب بدون كتابته لقرص أولاً.
import pandas as pd

from app.core_logic._logger import get_logger

log = get_logger()

POSSIBLE_COLUMNS = {
    "item_name": [
        "اسم الصنف", "اسم المنتج", "اسم المادة",
        "البيان", "الوصف", "المادة", "الصنف/البيان",
        "item name", "item description", "description",
        "product name", "product description", "name",
    ],
    "category": [
        "التصنيف", "الفئة", "نوع الصنف",
        "الفئة/التصنيف", "category", "type", "الصنف",
    ],
    "unit": [
        "الوحدة", "وحدة", "العبوة", "عبوة",
        "الوحدة/العبوة", "unit",
    ],
    "boxes": [
        "الكمية", "كمية", "العدد", "qty", "quantity",
        "عدد الصناديق", "الصناديق", "عدد الكراتين",
        "الكمية بالصندوق", "boxes", "الكمية الإجمالية",
    ],
    "per_box": [
        "سعة الصندوق", "ب_الصندوق", "قطع/صندوق",
        "per_box", "سعة الكرتون", "ب الصندوق",
    ],
    "total_price": [
        "إجمالي سعر الصنف", "الإجمالي", "المبلغ",
        "إجمالي", "total", "Total", "المجموع",
        "إجمالي المبلغ", "القيمة الإجمالية",
    ],
    "cost_price": [
        "سعر الوحدة", "سعر الشراء", "سعر التكلفة",
        "السعر", "التكلفة", "cost", "price", "سعر",
        "سعر القطعة",
    ],
    "expiry_date": [
        "تاريخ الصلاحية", "تاريخ الانتهاء",
        "انتهاء الصلاحية", "الصلاحية", "الانتهاء",
        "exp. date", "expiry", "exp date",
    ],
    "discount_pct": [
        "نسبة الخصم", "الخصم", "خصم", "discount", "discount %", "discount_pct",
    ],
    "supplier_item_code": [
        "كود الصنف", "الكود", "رمز الصنف", "sku", "item code", "product code",
    ],
}


def detect_header_row(df_raw: pd.DataFrame) -> int:
    for i, row in df_raw.iterrows():
        matches = 0
        for hints in POSSIBLE_COLUMNS.values():
            if any(
                str(hint).lower() in str(cell).strip().lower()
                for hint in hints
                for cell in row.values
                if pd.notna(cell)
            ):
                matches += 1
        if matches >= 2:
            return i
    return 0


# اسم المورد بالصياغة "تسمية: قيمة" (بنفس الخلية) أو "تسمية بخلية / قيمة بالخلية اللي
# بعدها بنفس الصف" — نبحث عنه صراحة بدل افتراض إن أول خلية بالملف (A1) هي اسم المورد
# دايماً، لأنها غالباً عنوان/ترحيب عام ("بيانات الفاتورة"، "فاتورة مبيعات"...) مو اسم فعلي.
# طبقتين: تسمية دقيقة أولاً ("اسم المورد")، وإلا تسمية عامة ("المورد") مع استبعاد خلايا
# واضح إنها حقل ثاني (عنوان/هاتف/رقم ضريبي) بدل اسم المورد نفسه.
_SUPPLIER_LABEL_STRICT = ["اسم المورد", "supplier name"]
_SUPPLIER_LABEL_LOOSE = ["المورد", "vendor", "supplier"]
_SUPPLIER_LABEL_EXCLUDE = ["عنوان", "هاتف", "جوال", "رقم", "ضريب", "address", "phone", "tax"]


def _supplier_value_from_row(cells: list, label_idx: int) -> str:
    cell = cells[label_idx]
    if ":" in cell:
        _, _, after = cell.partition(":")
        after = after.strip()
        if after and after.lower() != "nan":
            return after
    for nxt in cells[label_idx + 1:]:
        if nxt and nxt.lower() != "nan":
            return nxt
    return ""


def extract_supplier_name(df_raw: pd.DataFrame) -> str:
    rows = [[str(c).strip() for c in row.values] for _, row in df_raw.iterrows()]

    for hints in (_SUPPLIER_LABEL_STRICT, _SUPPLIER_LABEL_LOOSE):
        for cells in rows:
            for j, cell in enumerate(cells):
                if not cell or cell.lower() == "nan":
                    continue
                cell_lower = cell.lower()
                if hints is _SUPPLIER_LABEL_LOOSE and any(ex in cell_lower for ex in _SUPPLIER_LABEL_EXCLUDE):
                    continue
                if any(h in cell_lower for h in hints):
                    value = _supplier_value_from_row(cells, j)
                    if value:
                        return value

    # fallback: أول خلية غير فاضية (لملفات قديمة بلا أي تسمية صريحة للمورد)
    try:
        val = str(df_raw.iloc[0, 0]).strip()
        if val and val.lower() != "nan":
            return val
    except Exception:
        pass
    return ""


def extract_from_excel(file_path_or_buffer):
    df_blind = pd.read_excel(file_path_or_buffer, header=None)
    supplier_name = extract_supplier_name(df_blind)
    header_row = detect_header_row(df_blind)
    log.info(f"[استخراج] رأس الجدول اكتُشف بالصف {header_row} — المورد: {supplier_name or 'غير محدد'}")

    # قراءة ثانية من بداية الملف — buffer بالذاكرة يحتاج seek(0) بعد أول قراءة، عكس مسار قرص
    if hasattr(file_path_or_buffer, "seek"):
        file_path_or_buffer.seek(0)
    df_raw = pd.read_excel(file_path_or_buffer, header=header_row)
    df_raw.columns = df_raw.columns.astype(str).str.strip()
    return df_raw, supplier_name
