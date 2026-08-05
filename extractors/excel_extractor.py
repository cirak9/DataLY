# extractors/excel_extractor.py — v6
import pandas as pd
from utils.logger import get_logger

log = get_logger()

POSSIBLE_COLUMNS = {
    "item_name": [
        "اسم الصنف", "اسم المنتج", "اسم المادة",
        "البيان", "الوصف", "المادة", "الصنف/البيان",
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


def extract_supplier_name(df_raw: pd.DataFrame) -> str:
    try:
        val = str(df_raw.iloc[0, 0]).strip()
        if val and val.lower() != "nan":
            return val
    except Exception:
        pass
    return ""


def extract_from_excel(file_path: str):
    df_blind = pd.read_excel(file_path, header=None)
    supplier_name = extract_supplier_name(df_blind)
    header_row = detect_header_row(df_blind)
    log.info(f"[استخراج] رأس الجدول اكتُشف بالصف {header_row} — المورد: {supplier_name or 'غير محدد'}")

    df_raw = pd.read_excel(file_path, header=header_row)
    df_raw.columns = df_raw.columns.astype(str).str.strip()
    return df_raw, supplier_name
