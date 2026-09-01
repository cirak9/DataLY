import pandas as pd
import os
from typing import Tuple
from utils.logger import get_logger

log = get_logger()

INVENTORY_POSSIBLE_COLUMNS = {
    'barcode': [
        'باركود', 'الباركود', 'كود', 'الكود', 'كود الصنف', 'رمز', 'الرمز',
        'code', 'barcode', 'bar code', 'sku', 'item code',
    ],
    'name': [
        'اسم الصنف', 'الاسم', 'اسم المنتج', 'الصنف', 'الوصف', 'وصف الصنف',
        'name', 'product_name', 'product name', 'item name', 'description',
    ],
    'expiration': [
        'صلاحية', 'الصلاحية', 'انتهاء', 'تاريخ الانتهاء', 'تاريخ الصلاحية',
        'expiration', 'expiry', 'exp date', 'exp. date',
    ],
}


def _find_inventory_column(columns: list, hints: list, exact: bool) -> str:
    for hint in hints:
        h = hint.lower().strip()
        for col in columns:
            col_lower = col.lower().strip()
            if (col_lower == h) if exact else (h in col_lower):
                return col
    return None


def detect_inventory_columns(df: pd.DataFrame) -> Tuple[str, str, str]:
    """
    تحديد أعمدة المخزون تلقائياً من أي ملف — تطابق تام أول لكل الأعمدة الثلاثة،
    وبعدين تطابق تقريبي (احتواء) لأي عمود لسا ناقص، عشان صيغ شائعة زي "الباركود"
    بألف التعريف أو تسميات المنظومة المختلفة ما توقف البرنامج بدون داعي.

    Returns:
        (barcode_col, name_col, expiration_col)
    """
    columns = [col.strip() for col in df.columns]

    barcode_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS['barcode'], exact=True)
    name_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS['name'], exact=True)
    expiration_col = _find_inventory_column(columns, INVENTORY_POSSIBLE_COLUMNS['expiration'], exact=True)

    remaining = [c for c in columns if c not in (barcode_col, name_col, expiration_col)]
    if barcode_col is None:
        barcode_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS['barcode'], exact=False)
        remaining = [c for c in remaining if c != barcode_col]
    if name_col is None:
        name_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS['name'], exact=False)
        remaining = [c for c in remaining if c != name_col]
    if expiration_col is None:
        expiration_col = _find_inventory_column(remaining, INVENTORY_POSSIBLE_COLUMNS['expiration'], exact=False)

    if not barcode_col or not name_col or not expiration_col:
        missing = []
        if not barcode_col:
            missing.append('الباركود')
        if not name_col:
            missing.append('اسم الصنف')
        if not expiration_col:
            missing.append('الصلاحية')

        raise ValueError(f"الأعمدة المطلوبة غير موجودة: {', '.join(missing)}")

    return barcode_col, name_col, expiration_col


def extract_old_inventory(inventory_path: str) -> pd.DataFrame:
    """
    استخراج مخزون المتجر القديم

    Args:
        inventory_path: مسار ملف المخزون

    Returns:
        DataFrame بأعمدة: barcode, name, expiration
    """
    if not os.path.exists(inventory_path):
        log.warning(f"ملف المخزون غير موجود: {inventory_path}")
        return pd.DataFrame(columns=['barcode', 'name', 'expiration'])

    try:
        df = pd.read_excel(inventory_path)
        log.info(f"تم قراءة المخزون: {len(df)} صنف")

        barcode_col, name_col, expiration_col = detect_inventory_columns(df)

        # إعادة تسمية الأعمدة
        df = df[[barcode_col, name_col, expiration_col]].copy()
        df.columns = ['barcode', 'name', 'expiration']

        # تنظيف الباركود
        df['barcode'] = df['barcode'].astype(str).str.strip()
        df['name'] = df['name'].astype(str).str.strip()
        df['expiration'] = df['expiration'].astype(str).str.strip()

        # إزالة الصفوف الفارغة
        df = df[df['barcode'] != ''].dropna()

        return df

    except Exception as e:
        log.error(f"خطأ في قراءة المخزون: {e}")
        raise


def extract_supplier_inventory(supplier_path: str) -> pd.DataFrame:
    """
    استخراج مخزون المورد

    Args:
        supplier_path: مسار ملف مخزون المورد

    Returns:
        DataFrame بأعمدة: barcode, name, expiration
    """
    if not os.path.exists(supplier_path):
        log.warning(f"ملف مخزون المورد غير موجود: {supplier_path}")
        return pd.DataFrame(columns=['barcode', 'name', 'expiration'])

    try:
        df = pd.read_excel(supplier_path)
        log.info(f"تم قراءة مخزون المورد: {len(df)} صنف")

        barcode_col, name_col, expiration_col = detect_inventory_columns(df)

        # إعادة تسمية الأعمدة
        df = df[[barcode_col, name_col, expiration_col]].copy()
        df.columns = ['barcode', 'name', 'expiration']

        # تنظيف البيانات
        df['barcode'] = df['barcode'].astype(str).str.strip()
        df['name'] = df['name'].astype(str).str.strip()
        df['expiration'] = df['expiration'].astype(str).str.strip()

        # إزالة الصفوف الفارغة
        df = df[df['barcode'] != ''].dropna()

        return df

    except Exception as e:
        log.error(f"خطأ في قراءة مخزون المورد: {e}")
        raise
