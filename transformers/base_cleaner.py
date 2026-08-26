# transformers/base_cleaner.py — v6
import re
import pandas as pd
from extractors.excel_extractor import POSSIBLE_COLUMNS
from utils.validators import validate_extracted_columns, validate_clean_dataframe
from utils.logger import get_logger

log = get_logger()

TOTAL_KEYWORDS = [
    "المجموع", "الإجمالي", "مجموع", "إجمالي",
    "subtotal", "total", "grand total",
    "الخصم", "خصم", "discount",
    "الضريبة", "ضريبة", "vat", "tax",
    "صافي", "net",
]

NOTE_KEYWORDS = [
    "ملاحظ", "ملاحظة", "شروط", "سياسة",
    "البضاعة", "المباعة", "لا تُرد", "لا ترد",
    "يُرجى", "يرجى", "سداد", "المبلغ",
    "الأجل", "تعليق الحساب", "توقيع", "استلام العميل",
    "note", "terms", "conditions",
]

NUMBERED_NOTE_PATTERN = re.compile(r"^\s*[\d١٢٣٤٥٦٧٨٩٠]+\s*[.\-\)]\s*.{10,}")


def _find_column(df_columns: list, possible_names: list, already_used: set):
    for hint in possible_names:
        for col in df_columns:
            if col in already_used:
                continue
            if hint.lower() == str(col).strip().lower():
                return col
    for hint in possible_names:
        for col in df_columns:
            if col in already_used:
                continue
            if hint.lower() in str(col).strip().lower():
                return col
    return None


def _clean_number(val) -> float:
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0.0
        cleaned = (
            str(val).replace(",", "").replace("،", "")
            .replace(" ", "").replace("د.ل", "").strip()
        )
        if not cleaned:
            return 0.0
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _is_note_or_total_row(val: str) -> bool:
    v = str(val).strip()
    if not v or v.lower() == "nan":
        return True
    vl = v.lower()
    for kw in TOTAL_KEYWORDS + NOTE_KEYWORDS:
        if kw.lower() in vl:
            return True
    if NUMBERED_NOTE_PATTERN.match(v):
        return True
    if len(v) > 60 and not any(c.isdigit() for c in v[:20]):
        return True
    return False


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    already_used: set = set()
    rename_map: dict = {}

    for standard_col, possible_names in POSSIBLE_COLUMNS.items():
        found = _find_column(list(df.columns), possible_names, already_used)
        if found:
            rename_map[found] = standard_col
            already_used.add(found)

    df = df.rename(columns=rename_map)

    validate_extracted_columns(df)  # 🆕 يوقف برسالة واضحة لو "اسم الصنف" مفقود

    desired = [
        "item_name", "category", "unit",
        "boxes", "per_box", "total_price", "cost_price", "expiry_date",
        "discount_pct", "supplier_item_code",
    ]
    existing = [c for c in desired if c in df.columns]
    df = df[existing].copy()

    if "item_name" in df.columns:
        df["item_name"] = df["item_name"].astype(str).str.strip()
        df = df[df["item_name"].notna()]
        df = df[df["item_name"] != ""]
        df = df[df["item_name"].str.lower() != "nan"]
        df = df[~df["item_name"].apply(_is_note_or_total_row)]

    for col in ["category", "unit", "supplier_item_code"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            df[col] = df[col].replace(["nan", "None"], "")

    for col in ["boxes", "per_box", "total_price", "cost_price", "discount_pct"]:
        if col in df.columns:
            df[col] = df[col].map(_clean_number)

    if "expiry_date" in df.columns:
        df["expiry_date"] = (
            pd.to_datetime(df["expiry_date"], errors="coerce", dayfirst=True)
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )

    has_qty = "boxes" in df.columns
    has_price = "total_price" in df.columns or "cost_price" in df.columns
    if has_qty and has_price:
        price_col = "total_price" if "total_price" in df.columns else "cost_price"
        df = df[~((df["boxes"] == 0) & (df[price_col] == 0))]

    df = df.reset_index(drop=True)
    df.insert(0, "item_id", range(1, len(df) + 1))

    validate_clean_dataframe(df)  # 🆕 تحقق نهائي: ما فيه كميات/أسعار سالبة، ما فيه جدول فاضي

    return df
