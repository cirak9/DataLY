import pandas as pd
import os
from collections import Counter
from typing import Tuple
from utils.logger import get_logger
from utils import barcode_categories
from utils.categorizer import CATEGORY_ENTRIES, get_category

log = get_logger()

# {تصنيف فرعي معروف -> تصنيفه الرئيسي} كبذرة أولية من utils/categories.json — تُستخدم فقط
# كخطوة أولى بمقارنة "هل هذا الفرعي معروف؟" قبل اللجوء لفهرس barcode_categories المتراكم
# أو لتخمين الاسم. ملفات الجرد ما فيها عمود تصنيف رئيسي (سهل يُشتق) — اللي فيها هو الفرعي
# فقط (الأصعب والأدق)، فهذا يخدم أول تشغيلة قبل ما الفهرس المتراكم يكبر.
_KNOWN_SUB_TO_MAIN = {entry["sub"].strip(): entry["main"].strip() for entry in CATEGORY_ENTRIES}

INVENTORY_POSSIBLE_COLUMNS = {
    'barcode': [
        'باركود', 'الباركود', 'كود', 'الكود', 'كود الصنف', 'رمز', 'الرمز',
        'code', 'barcode', 'bar code', 'sku', 'item code',
    ],
    'name': [
        'اسم الصنف', 'الاسم', 'اسم المنتج', 'الصنف', 'الوصف', 'وصف الصنف',
        'name', 'product_name', 'product name', 'item name', 'description',
        # 'descr' يُطابَق أخيراً بالمرحلة التامة، بعد 'name' الصريح — عمود اسمه حرفياً "name"
        # (زي ملف نتج عن دمج سابق بأداتنا) أولى دايماً من "descR" المختصر (نظام نقاط بيع
        # خارجي شائع، راجع الكوميت). لسا قبل مرحلة التخمين التقريبي عشان ما يمسك "item_name"
        # (تصنيف/تجميع مو اسم الصنف فعلياً) غلط لو "descR" و"name" الاثنين غير موجودين.
        'descr',
    ],
    'expiration': [
        'صلاحية', 'الصلاحية', 'انتهاء', 'تاريخ الانتهاء', 'تاريخ الصلاحية',
        'expiration', 'expiry', 'exp date', 'exp. date',
        'date_xp',  # نفس نظام نقاط البيع فوق — عمود تاريخ الصلاحية اسمه "date_xp"
    ],
}

# عمود التصنيف الفرعي اختياري تماماً (بخلاف الثلاثة فوق) — لا يوجد عمود "تصنيف رئيسي"
# بملفات الجرد أصلاً (الرئيسي سهل يُشتق تلقائياً)، اللي يجينا فعلياً هو الفرعي بس (الأصعب
# والأدق). لو موجود بأي ملف جرد (متجر أو مورد)، نغذّي منه فهرس barcode_categories المركزي
# المشترك بين كل المتاجر. لو مو موجود، نتجاهل بصمت — ما هو شرط لنجاح استخراج الجرد.
CATEGORY_POSSIBLE_COLUMNS = {
    'sub': [
        'التصنيف الفرعي', 'الفئة الفرعية', 'فرعي', 'القسم الفرعي', 'التصنيف', 'الفئة',
        'sub category', 'subcategory', 'sub-category', 'category',
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


def detect_subcategory_column(df: pd.DataFrame, exclude: set) -> str:
    """
    تحديد عمود التصنيف الفرعي إن وُجد — اختياري بالكامل، بدون رفع خطأ لو غير موجود
    (بخلاف detect_inventory_columns). لا يوجد عمود "رئيسي" يُبحث عنه إطلاقاً (راجع
    CATEGORY_POSSIBLE_COLUMNS).

    أولاً بعنوان صريح (تام ثم تقريبي). وإلا: أي عمود إضافي نصي (مو رقمي ولا تاريخ) وقيمه
    متكررة بكثافة (عدد القيم الفريدة أقل بكثير من عدد الصفوف — إشارة تجميع/تصنيف نموذجية،
    زي "item_name" بملفات أنظمة نقاط بيع حقيقية: 31 قيمة فريدة بس عبر مئات الصفوف، بعنوان
    عمود مضلِّل يوحي بأنه اسم الصنف بينما هو فعلياً تصنيف). ما نشترط تطابق مسبق مع تصنيفات
    معروفة (بذرة categories.json أو الفهرس المتراكم) — هذا يفشل بأول ملف حقيقي قبل ما
    يتراكم أي شي بالفهرس؛ التكرار بالقيم نفسها كافٍ كإشارة. لو فيه أكثر من مرشح، نفضّل
    الأقل تكراراً (أوضح كتصنيف)، وبعدين الأعلى تطابقاً مع المعروف مسبقاً كمرجّح إضافي.

    Returns:
        اسم العمود، أو None لو ما انلقى شي
    """
    columns = [c for c in df.columns if c not in exclude]

    sub_col = _find_inventory_column(columns, CATEGORY_POSSIBLE_COLUMNS['sub'], exact=True)
    if sub_col is None:
        sub_col = _find_inventory_column(columns, CATEGORY_POSSIBLE_COLUMNS['sub'], exact=False)
    if sub_col:
        return sub_col

    def _is_known(v) -> bool:
        s = str(v).strip()
        if not s or s.lower() in ("nan", "none"):
            return False
        return s in _KNOWN_SUB_TO_MAIN or barcode_categories.main_for_sub(s) is not None

    candidates = []
    for col in columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
            continue  # التصنيف نص مقروء دايماً، مو رقم/تاريخ

        non_empty_mask = s.apply(lambda v: str(v).strip() not in ("", "nan", "none"))
        n = int(non_empty_mask.sum())
        if n == 0:
            continue

        unique_count = s[non_empty_mask].astype(str).str.strip().nunique()
        cardinality_ratio = unique_count / n
        known_ratio = s.apply(_is_known).sum() / n

        # يتأهل العمود بأي من إشارتين: تكرار واضح بالقيم (تصنيف/تجميع نموذجي حتى لو
        # فرعي جديد كلياً غير معروف بعد)، أو غالبية قيمه معروفة مسبقاً حتى لو الملف صغير
        # (صف واحد أو صفين، ما يكفي لإظهار تكرار، لكن القيمة نفسها معروفة من ملف سابق).
        repeats = unique_count >= 2 and cardinality_ratio <= 0.5
        if not repeats and known_ratio < 0.5:
            continue

        candidates.append((cardinality_ratio, -known_ratio, col))

    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def _learn_categories_if_present(df: pd.DataFrame, barcode_col: str, name_col: str,
                                  expiration_col: str, store_id: str, source: str) -> None:
    """
    مسار واحد بس لتغذية فهرس barcode_categories المركزي من ملف الجرد: نحدد عمود التصنيف
    الفرعي (detect_subcategory_column) — لا يوجد عمود رئيسي بالملف أصلاً، الرئيسي دايماً
    يُشتق تلقائياً وليس مقروءاً من عمود:
      - لو الفرعي معروف مسبقاً (ببذرة categories.json أو بفهرس barcode_categories المتراكم
        من ملف سابق لأي متجر) → يُعتمد نفس رئيسيه المعروف، ويُضاف هذا الصنف تحته.
      - لو الفرعي جديد كلياً (أول مرة يُشاف بالنظام) → رئيسيه يُشتق من اسم الصنف بنفس نظام
        تخمين الكلمات المفتاحية الحالي (categorizer.get_category)، ويُعتمد الفرعي كما هو
        بالملف (المصدر الموثوق) — فيصير هذا الفرعي نفسه معروفاً لأي ملف لاحق.
    ميزة إضافية بالكامل: لو ما فيه عمود تصنيف فرعي يُكتشف بالملف، نتجاهل بصمت — استخراج
    الجرد (بدون هذا الملف، أو بملف مورد بدل متجر، أو العكس) يشتغل عادي بدون أي أثر.
    """
    sub_col = detect_subcategory_column(df, exclude={barcode_col, name_col, expiration_col})
    if not sub_col:
        return

    def _clean(v) -> str:
        s = str(v).strip()
        return "" if not s or s.lower() in ("nan", "none") else s

    rows = [
        (row.get(barcode_col, ""), _clean(row.get(sub_col, "")),
         _clean(row.get(name_col, "")) if name_col else "")
        for _, row in df.iterrows()
    ]
    rows = [r for r in rows if r[1]]  # استبعاد صفوف بلا تصنيف فرعي

    # رئيسي كل فرعي جديد كلياً بهذا الملف = تصويت أغلبية على تخمين كل أصنافه من اسمها
    # (بدل الاعتماد على أول صنف بس بالملف) — يمنع تخمين فردي غلط (تشابه لفظي عرضي، زي
    # "كورن" مقابل "كلور" بتخمين الكلمات المفتاحية) من تلويث تصنيف فرعي كامل مشترك بين
    # عشرات الأصناف؛ ويضمن رئيسياً واحداً متّسقاً لكل الأصناف بنفس الفرعي بهذا الملف.
    unresolved_subs = {
        sub for _, sub, _ in rows
        if sub not in _KNOWN_SUB_TO_MAIN and barcode_categories.main_for_sub(sub) is None
    }
    batch_main = {}
    for sub in unresolved_subs:
        guesses = [get_category(name)[0] for _, s, name in rows if s == sub]
        batch_main[sub] = Counter(guesses).most_common(1)[0][0]

    records = []
    for barcode, sub_val, name_val in rows:
        main_val = (_KNOWN_SUB_TO_MAIN.get(sub_val)
                    or barcode_categories.main_for_sub(sub_val)
                    or batch_main.get(sub_val))
        records.append((barcode, main_val, sub_val, name_val, store_id))

    learned = barcode_categories.learn_many(records)
    if learned:
        log.info(f"[{source}] فهرس التصنيف المركزي: {learned} صنف اعتُمد تحت تصنيفه الفرعي "
                 f"(من عمود '{sub_col}')")


def extract_old_inventory(inventory_path: str, store_id: str = "") -> pd.DataFrame:
    """
    استخراج مخزون المتجر القديم

    Args:
        inventory_path: مسار ملف المخزون
        store_id: معرف المتجر (اختياري) — يُسجَّل كمصدر لو الملف فيه عمود تصنيف فرعي
            يُستفاد منه لفهرس barcode_categories المركزي

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
        _learn_categories_if_present(df, barcode_col, name_col, expiration_col, store_id, "مخزون متجر")

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


def extract_supplier_inventory(supplier_path: str, store_id: str = "") -> pd.DataFrame:
    """
    استخراج مخزون المورد

    Args:
        supplier_path: مسار ملف مخزون المورد
        store_id: معرف المتجر (اختياري) — يُسجَّل كمصدر لو الملف فيه عمود تصنيف فرعي
            يُستفاد منه لفهرس barcode_categories المركزي

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
        _learn_categories_if_present(df, barcode_col, name_col, expiration_col, store_id, "مخزون مورد")

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
