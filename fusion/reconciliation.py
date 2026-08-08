# fusion/reconciliation.py — v6.1
# خطوة توحيد الأصناف: تُستدعى بعد اكتمال جلسة التاجر، قبل merge_invoice_and_session().
# تقارن اسم الصنف بـ invoice_data.xlsx مقابل قاعدة master_items.xlsx (عبر الباركود من
# session_output.xlsx)، فتوحّد نفس الصنف اللي كل مورد يكتبه بصيغة مختلفة.
import os
import re
import pandas as pd
from rapidfuzz import fuzz, process
from utils.logger import get_logger

log = get_logger()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MASTER_ITEMS_PATH = os.path.join(DATA_DIR, "master_items.xlsx")
REVIEW_PATH = os.path.join(DATA_DIR, "reconciliation_review.xlsx")

MASTER_COLUMNS = ["الباركود", "اسم الصنف", "التصنيف الرئيسي", "التصنيف الفرعي"]
CATEGORY_COLUMNS = ("التصنيف الرئيسي", "التصنيف الفرعي")

# كل متجر يجيك ملف قاعدة أصنافه بتسمية أعمدة مختلفة شوي حسب منظومته (السهل يسمي
# الباركود "الكود" والاسم "الوصف" مثلاً بملفات فاتورة مشتريات الحقيقية). نفس أسلوب
# POSSIBLE_COLUMNS بـ extractors/excel_extractor.py — قائمة واسعة تُعدَّل كل ما جربنا
# ملف حقيقي جديد من متجر/منظومة مختلفة.
MASTER_POSSIBLE_COLUMNS = {
    "الباركود": [
        "الباركود", "باركود", "الكود", "كود", "كود الصنف", "كود المنتج", "كود السلعة",
        "رمز الصنف", "رمز المنتج", "رمز السلعة", "الرمز", "رمز", "الترميز",
        "الرمز الشريطي", "رقم الصنف", "رقم المنتج", "الرقم التسلسلي", "رقم تسلسلي",
        "كود الباركود", "الكود التسلسلي", "sku", "barcode", "bar code", "code",
        "item code", "product code", "upc", "ean", "gtin", "product id",
        "item id", "scan code",
    ],
    "اسم الصنف": [
        "اسم الصنف", "الاسم", "اسم المنتج", "اسم المادة", "اسم السلعة", "الصنف",
        "الوصف", "وصف الصنف", "وصف المنتج", "البيان", "المادة",
        "تسمية الصنف", "تسمية المنتج", "مسمى الصنف", "مسمى المنتج", "التسمية",
        "name", "item name", "product name", "description",
        "item description", "product description", "title",
    ],
    "التصنيف الرئيسي": [
        "التصنيف الرئيسي", "التصنيف", "الفئة الرئيسية", "الفئة", "رئيسي", "القسم",
        "القسم الرئيسي", "التبويب", "category", "main category", "group",
    ],
    "التصنيف الفرعي": [
        "التصنيف الفرعي", "الفئة الفرعية", "فرعي", "القسم الفرعي", "التبويب الفرعي",
        "sub category", "subcategory", "sub-category",
    ],
}


class MasterDataError(Exception):
    """يُرفع لو ملف master_items.xlsx ما فيه عمود يمكن التعرّف عليه كباركود أو كاسم للصنف."""
    pass

# باركود مطابق لكن الاسم مختلف عن كذا → "تنبيه" يُعرض مع التطابق المُقترَح وقت طلب الموافقة
# (مو رفض تلقائي — كل تطابق بالباركود يُعرض للموافقة بغض النظر عن هذا الحد). الحد منخفض
# عمدًا: الباركود نفسه دليل هوية قوي، فنفس الصنف قد يُكتب بصيغ عربية مختلفة كثيرًا (مثال:
# "أرز أبيض ممتاز 5 كجم" مقابل "رز ابيض فاخر 5ك" ≈ 63 بمقياس WRatio) — التنبيه يظهر فقط
# للتعارض الحقيقي المحتمل (صنف مختلف تمامًا وصل لنفس الباركود بالخطأ).
CONFLICT_THRESHOLD = 45
# لا يوجد باركود بالفاتورة → يُقترَح تطابق بالاسم التقريبي (وينتظر موافقتك بردو) فقط لو
# التشابه ≥ كذا؛ أقل من كذا يُعتبر "بلا مطابقة معروفة" ولا يُقترَح إطلاقًا. الحد أعلى من
# CONFLICT_THRESHOLD لأنه بدون باركود لا يوجد مرساة هوية، فنطلب ثقة أعلى قبل حتى الاقتراح.
FUZZY_MATCH_THRESHOLD = 60

# WRatio يقيس تشابه النص الكلي بس — "سكر ناعم 10 كجم" و"سكر التميز 1 كغ" يطلعوا متشابهين
# نصيًا (كلمة "سكر" و"كجم"/"كغ" مشتركة) رغم إن الحجم مختلف كليًا (10 أضعاف). هذا فرق حجم
# حقيقي غالبًا يدل على باركود مُدخل غلط لعبوة مختلفة، مو مجرد صياغة مختلفة لنفس الصنف —
# فنقارن الوزن/الحجم المستخرج من الاسمين كفحص إضافي مستقل عن WRatio.
_WEIGHT_UNITS = {"كجم": 1000, "كغ": 1000, "كيلوجرام": 1000, "كيلو": 1000,
                 "جرام": 1, "غرام": 1, "جم": 1, "غ": 1}
_VOLUME_UNITS = {"لتر": 1000, "لترات": 1000, "مل": 1, "مليلتر": 1}
_SIZE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" +
    "|".join(sorted({**_WEIGHT_UNITS, **_VOLUME_UNITS}, key=len, reverse=True)) +
    r")\b"
)
# فرق الحجم المسموح بيه قبل ما يُعتبر تعارض — يتحمّل فروقات تعبئة بسيطة (900غ مقابل 1كجم)
# لكن يلتقط فرق حجم حقيقي (10كجم مقابل 1كجم).
SIZE_MISMATCH_RATIO = 1.3


def _extract_size(name: str):
    """يستخرج (القيمة بوحدة أساسية، الفئة) من اسم الصنف — وزن بالغرام أو حجم بالمليلتر.
    يرجع None لو ما لقى وحدة وزن/حجم معروفة (يشمل اختصارات غامضة زي '5ك')."""
    match = _SIZE_PATTERN.search(name)
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2)
    if unit in _WEIGHT_UNITS:
        return value * _WEIGHT_UNITS[unit], "weight"
    return value * _VOLUME_UNITS[unit], "volume"


def _size_conflict_reason(name_a: str, name_b: str) -> str:
    """يرجع سبب تعارض الحجم/الوزن لو موجود، أو "" لو ما فيه تعارض. غموض أو تعذّر
    استخراج حجم من أحد الاسمين = بلا تعارض (نعتمد عندها على WRatio وحده، تفاديًا
    لإنذارات كاذبة من حالات ما نقدر نجزم فيها)."""
    size_a, size_b = _extract_size(name_a), _extract_size(name_b)
    if not size_a or not size_b:
        return ""
    val_a, cat_a = size_a
    val_b, cat_b = size_b
    if cat_a != cat_b:
        # نوع القياس نفسه مختلف (وزن مقابل حجم) — ما نقدر نقارن الأرقام رياضيًا،
        # لكن الاختلاف بحد ذاته مؤشر شك كافٍ يستاهل مراجعة بشرية.
        return "نوع القياس نفسه مختلف بين الاسمين (وزن مقابل حجم) — راجع يدويًا للتأكد إنه نفس الصنف"
    if val_a and val_b and max(val_a, val_b) / min(val_a, val_b) >= SIZE_MISMATCH_RATIO:
        return "الحجم/الوزن مختلف كليًا (مو مجرد صياغة مختلفة)"
    return ""


def _clean_str(val) -> str:
    s = str(val).strip() if val is not None else ""
    return "" if s.lower() in ("nan", "none") else s


def _find_column(df_columns: list, possible_names: list, already_used: set):
    """يبحث عن عمود مطابق تمامًا أول، وإلا مطابقة جزئية — بنفس أسلوب _find_column
    بـ transformers/base_cleaner.py، مطبّق هنا على أسماء أعمدة master منفصلة عمدًا
    (نطاق دلالي مختلف عن أعمدة الفاتورة)."""
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


def load_master(path: str = MASTER_ITEMS_PATH) -> pd.DataFrame:
    """
    يحمّل master_items.xlsx، أو جدول فاضي بنفس الأعمدة لو الملف مو موجود بعد (أول تشغيلة).
    يتعرّف تلقائيًا على أسماء الأعمدة الحقيقية (زي "الكود"/"الوصف" بمنظومة السهل) بدل
    افتراض تسمية ثابتة، لأن كل متجر يجيك ملفه بتسمية مختلفة حسب منظومته.
    """
    if not os.path.exists(path):
        return pd.DataFrame(columns=MASTER_COLUMNS)

    df = pd.read_excel(path, dtype=str)
    df.columns = df.columns.astype(str).str.strip()

    already_used: set = set()
    rename_map: dict = {}
    for standard_col, hints in MASTER_POSSIBLE_COLUMNS.items():
        found = _find_column(list(df.columns), hints, already_used)
        if found:
            rename_map[found] = standard_col
            already_used.add(found)
    df = df.rename(columns=rename_map)

    if "اسم الصنف" not in df.columns:
        raise MasterDataError(
            "تعذّر إيجاد عمود اسم الصنف بملف master_items.xlsx. "
            "تأكد إن رأس الجدول فيه عمود بأحد هذي الأسماء أو ما يقاربها: "
            "'اسم الصنف' / 'الاسم' / 'الوصف' / 'اسم المنتج' / 'البيان'. "
            "لو اسم العمود عندك مختلف، أضفه لقائمة "
            "MASTER_POSSIBLE_COLUMNS['اسم الصنف'] بملف fusion/reconciliation.py."
        )
    if "الباركود" not in df.columns:
        raise MasterDataError(
            "تعذّر إيجاد عمود الباركود/الكود بملف master_items.xlsx. "
            "المطابقة بالكامل مبنية على الباركود، فبدونه ما فيه فايدة حقيقية من الملف. "
            "تأكد إن رأس الجدول فيه عمود بأحد هذي الأسماء أو ما يقاربها: "
            "'الباركود' / 'الكود' / 'كود الصنف' / 'رمز الصنف' / 'SKU'. "
            "لو اسم العمود عندك مختلف، أضفه لقائمة "
            "MASTER_POSSIBLE_COLUMNS['الباركود'] بملف fusion/reconciliation.py."
        )

    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(_clean_str)

    return df[MASTER_COLUMNS]


def save_master(df: pd.DataFrame, path: str = MASTER_ITEMS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = df.drop_duplicates(subset=["الباركود"], keep="last").reset_index(drop=True)
    df.to_excel(path, index=False)


def save_review(rows: list, path: str = REVIEW_PATH) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(rows).to_excel(path, index=False)
    log.info(f"[مطابقة] سجل قرارات التطابق ({len(rows)} حالة) → {path}")


def reconcile_dataframes(
    df_inv: pd.DataFrame,
    df_ses: pd.DataFrame,
    master_df: pd.DataFrame,
    conflict_threshold: int = CONFLICT_THRESHOLD,
    fuzzy_threshold: int = FUZZY_MATCH_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list]:
    """
    تحضّر التغييرات المقترحة على "اسم الصنف" (والتصنيف إن توفر) بـ df_inv مقابل
    master_df، بالاعتماد على الباركود المُدخل بـ df_ses. **لا تستبدل أي اسم تلقائيًا** —
    كل تطابق يرجع كـ"تطابق مُقترَح" ضمن pending_matches بانتظار موافقة بشرية عبر
    resolve_matches_interactively()، عدا تسجيل صنف جديد كليًا فهذا فقط تلقائي فورًا
    (إضافة جديدة، مو تعديل على شي معتمد من قبل).

    قواعد المطابقة:
    - باركود موجود بـ master  → تطابق مُقترَح (بالاسم/التصنيف المعتمد)، ينتظر موافقتك
      دائمًا مهما كانت نسبة التشابه — مع "تنبيه" لو الاسم مختلف كثيرًا أو الحجم/الوزن متعارض.
    - باركود غير موجود بـ master → صنف جديد، يُسجَّل تلقائيًا فورًا بنفس الاسم الحالي
      (بدون انتظار موافقة — هذا وضع طبيعي، لا شي معتمد سابقًا يتغيّر).
    - بدون باركود إطلاقًا      → لو فيه تشابه اسم كافٍ (fuzzy) مع صنف بـmaster وبدون تعارض
      حجم/وزن، يرجع كتطابق مُقترَح بردو ينتظر موافقتك. أقل من كذا = صنف بلا مطابقة معروفة
      (طبيعي، بدون اقتراح).

    يرجع (invoice، session، master محدّث بالأصناف الجديدة، قائمة pending_matches).
    """
    df_inv = df_inv.copy()
    df_ses = df_ses.copy()
    master_df = master_df.copy()
    for col in MASTER_COLUMNS:
        if col not in master_df.columns:
            master_df[col] = ""

    df_ses["الباركود"] = df_ses.get("الباركود", "").apply(_clean_str) if "الباركود" in df_ses.columns else ""
    barcode_by_item = dict(zip(df_ses.get("item_id", []), df_ses.get("الباركود", [])))

    master_by_barcode = {
        row["الباركود"]: row for _, row in master_df.iterrows() if row["الباركود"]
    }
    known_names = master_df["اسم الصنف"].tolist()

    pending_matches: list = []
    new_master_rows: list = []

    for _, inv_row in df_inv.iterrows():
        item_id = inv_row["item_id"]
        current_name = _clean_str(inv_row.get("اسم الصنف", ""))
        barcode = barcode_by_item.get(item_id, "")

        if barcode and barcode in master_by_barcode:
            approved = master_by_barcode[barcode]
            approved_name = approved["اسم الصنف"]
            similarity = fuzz.WRatio(current_name, approved_name)
            size_reason = _size_conflict_reason(current_name, approved_name)
            flag = size_reason or (
                "" if similarity >= conflict_threshold else "الاسم مختلف كثيرًا نصيًا عن الاسم المعتمد"
            )
            pending_matches.append({
                "item_id": item_id,
                "الباركود": barcode,
                "طريقة المطابقة": "باركود",
                "الاسم بالفاتورة": current_name,
                "الاسم المقترح": approved_name,
                "التصنيف الرئيسي المقترح": approved.get("التصنيف الرئيسي", ""),
                "التصنيف الفرعي المقترح": approved.get("التصنيف الفرعي", ""),
                "نسبة التشابه": round(similarity, 1),
                "تنبيه": flag,
            })

        elif barcode:
            # باركود جديد تمامًا على master → يدخل لأول مرة بنفس الاسم المكتوب بالفاتورة
            # تلقائيًا، بدون انتظار موافقة (إضافة جديدة، مو تعديل على شي معتمد سابقًا)
            new_master_rows.append({
                "الباركود": barcode,
                "اسم الصنف": current_name,
                "التصنيف الرئيسي": _clean_str(inv_row.get("التصنيف الرئيسي", "")),
                "التصنيف الفرعي": _clean_str(inv_row.get("التصنيف الفرعي", "")),
            })
            log.info(f"[مطابقة] صنف جديد كليًا سُجِّل تلقائيًا بالباركود {barcode}: '{current_name}'")

        elif known_names:
            # لا باركود بالمرة → fallback: مطابقة تقريبية للاسم فقط، بدون ربط بباركود
            match = process.extractOne(current_name, known_names, scorer=fuzz.WRatio)
            if match and match[1] >= fuzzy_threshold:
                matched_name = match[0]
                matched_row = master_df[master_df["اسم الصنف"] == matched_name].iloc[0]
                size_reason = _size_conflict_reason(current_name, matched_name)
                pending_matches.append({
                    "item_id": item_id,
                    "الباركود": "",
                    "طريقة المطابقة": "اسم تقريبي (بدون باركود)",
                    "الاسم بالفاتورة": current_name,
                    "الاسم المقترح": matched_name,
                    "التصنيف الرئيسي المقترح": matched_row.get("التصنيف الرئيسي", ""),
                    "التصنيف الفرعي المقترح": matched_row.get("التصنيف الفرعي", ""),
                    "نسبة التشابه": round(match[1], 1),
                    "تنبيه": size_reason,
                })
            # أقل من الحد → يُترك كما هو، صنف بلا مطابقة معروفة (طبيعي، بدون اقتراح)

    master_df = pd.concat([master_df, pd.DataFrame(new_master_rows, columns=MASTER_COLUMNS)],
                           ignore_index=True) if new_master_rows else master_df

    return df_inv, df_ses, master_df, pending_matches


def _merge_duplicate_barcodes(df_inv: pd.DataFrame, df_ses: pd.DataFrame, canonical_barcode: dict):
    """لو صفّين بنفس الفاتورة وصلوا لنفس الباركود المعتمد (نفس الصنف بصيغتين)، تُدمج لصف واحد."""
    groups: dict = {}
    for item_id, barcode in canonical_barcode.items():
        groups.setdefault(barcode, []).append(item_id)

    drop_ids = []
    for barcode, ids in groups.items():
        if len(ids) < 2:
            continue
        ids_sorted = sorted(ids)
        keep_id = ids_sorted[0]
        rows = df_inv[df_inv["item_id"].isin(ids_sorted)]

        total_qty = pd.to_numeric(rows.get("العدد", 0), errors="coerce").fillna(0).sum()
        total_boxes = pd.to_numeric(rows.get("الصندوق", 0), errors="coerce").fillna(0).sum()
        total_amount = pd.to_numeric(rows.get("الإجمالي", 0), errors="coerce").fillna(0).sum()
        new_unit_cost = round(total_amount / total_qty, 3) if total_qty else 0.0

        keep_idx = df_inv.index[df_inv["item_id"] == keep_id][0]
        df_inv.at[keep_idx, "العدد"] = total_qty
        df_inv.at[keep_idx, "الصندوق"] = round(total_boxes, 4)
        df_inv.at[keep_idx, "الإجمالي"] = round(total_amount, 3)
        df_inv.at[keep_idx, "تكلفة الوحدة"] = new_unit_cost

        drop_ids.extend(ids_sorted[1:])
        log.info(f"[مطابقة] دمج {len(ids_sorted)} صف لنفس الباركود {barcode} بصنف واحد (item_id={keep_id})")

    if drop_ids:
        df_inv = df_inv[~df_inv["item_id"].isin(drop_ids)].reset_index(drop=True)
        df_ses = df_ses[~df_ses["item_id"].isin(drop_ids)].reset_index(drop=True)

    return df_inv, df_ses


def resolve_matches_interactively(
    df_inv: pd.DataFrame, df_ses: pd.DataFrame, master_df: pd.DataFrame, pending_matches: list,
    choices=None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list]:
    """
    تعرض كل تطابق مُقترَح بالطرفية وتطلب قرارًا فوريًا — **كل تطابق، مهما كانت نسبة
    التشابه**، مو بس الحالات المتعارضة:
      [1] موافقة  — استخدم الاسم/التصنيف المقترح من master
      [2] رفض     — إبقاء الاسم الأصلي بالفاتورة كما هو (الافتراضي)
      [3] تسمية يدوية — اكتب الاسم الصحيح بنفسك الآن

    التسمية اليدوية تُحدَّث بالفاتورة و master_items.xlsx معًا (نفس فلسفة "يُصنَّف مرة
    وحدة ويُحفظ للأبد" — لو صححته الآن، ما يرجع يسألك عنه بنفس الباركود مرة ثانية).
    بعد كل القرارات، تُدمج تلقائيًا أي صفّين وصلوا لنفس الباركود المعتمد (بالموافقة أو
    التسمية اليدوية) بنفس الفاتورة.

    دالة منفصلة عمدًا عن reconcile_dataframes() (اللي تبقى pure/قابلة للاختبار بدون
    تدخل بشري) — تُستدعى فقط من reconcile() بالتشغيل الحقيقي. آمنة عند تشغيل غير
    تفاعلي (EOFError) — تفترض "رفض" (الاسم الأصلي) بدل ما تعلّق بانتظار إدخال ما راح يجي.

    `choices`: iterator اختياري يزوّد الردود بدل input() الحقيقي — للاختبارات فقط.
    """
    if not pending_matches:
        return df_inv, df_ses, master_df, []

    def _prompt(text: str) -> str:
        if choices is not None:
            return next(choices, "")
        try:
            return input(text).strip()
        except EOFError:
            return ""  # تشغيل غير تفاعلي — رفض افتراضي بدل ما تعلّق

    df_inv = df_inv.copy()
    master_df = master_df.copy()
    canonical_barcode: dict = {}

    for m in pending_matches:
        item_id, barcode = m["item_id"], m["الباركود"]
        print(f"\n🔎 تطابق مُقترَح ({m['طريقة المطابقة']}):")
        print(f"   بالفاتورة: {m['الاسم بالفاتورة']}")
        print(f"   المقترح:   {m['الاسم المقترح']}  (تشابه {m['نسبة التشابه']:.0f}%)")
        if m["تنبيه"]:
            print(f"   ⚠️ تنبيه: {m['تنبيه']}")

        choice = _prompt(
            "   [1] موافقة — استخدم الاسم المقترح   [2] رفض — إبقاء الاسم الأصلي   "
            "[3] تسمية يدوية\n   اختر (1/2/3) [افتراضي 2]: "
        )

        inv_idx = df_inv.index[df_inv["item_id"] == item_id][0]

        if choice == "1":
            df_inv.at[inv_idx, "اسم الصنف"] = m["الاسم المقترح"]
            for cat_key, cat_col in (("التصنيف الرئيسي المقترح", "التصنيف الرئيسي"),
                                      ("التصنيف الفرعي المقترح", "التصنيف الفرعي")):
                if m.get(cat_key):
                    df_inv.at[inv_idx, cat_col] = m[cat_key]
            if barcode:
                canonical_barcode[item_id] = barcode
            m["القرار"] = "موافقة — اعتُمد الاسم المقترح"
            log.info(f"[مطابقة] موافقة على '{m['الاسم المقترح']}' لـitem_id={item_id}")

        elif choice == "3":
            manual_name = _prompt("   اكتب الاسم الصحيح المعتمد: ")
            if manual_name:
                df_inv.at[inv_idx, "اسم الصنف"] = manual_name
                if barcode:
                    master_idx = master_df.index[master_df["الباركود"] == barcode]
                    if len(master_idx):
                        master_df.at[master_idx[0], "اسم الصنف"] = manual_name
                    canonical_barcode[item_id] = barcode
                m["القرار"] = f"تسمية يدوية: {manual_name}"
                log.info(f"[مطابقة] تسمية يدوية اعتُمدت للباركود {barcode}: '{manual_name}' (وتحدّث master)")
            else:
                m["القرار"] = "رفض — إبقاء الاسم الأصلي (لم يُكتب اسم يدوي)"

        else:
            m["القرار"] = "رفض — إبقاء الاسم الأصلي"

    df_inv, df_ses = _merge_duplicate_barcodes(df_inv, df_ses, canonical_barcode)

    return df_inv, df_ses, master_df, pending_matches


def reconcile() -> int:
    """غلاف الملفات: يقرأ invoice_data/session_output/master_items من data/، يوحّد الأصناف،
    يعرض أي تطابق مُقترَح بالطرفية لموافقة فورية (كل تطابق، مو بس المتعارض)، يكتب الملفات
    المحدّثة، ويرجّع عدد التطابقات اللي عُرضت للموافقة."""
    invoice_path = os.path.join(DATA_DIR, "invoice_data.xlsx")
    session_path = os.path.join(DATA_DIR, "session_output.xlsx")

    if not os.path.exists(invoice_path):
        raise FileNotFoundError(f"invoice_data.xlsx غير موجود في {DATA_DIR}")
    if not os.path.exists(session_path):
        raise FileNotFoundError(f"session_output.xlsx غير موجود في {DATA_DIR}")

    df_inv = pd.read_excel(invoice_path)
    df_ses = pd.read_excel(session_path, dtype={"الباركود": str})
    df_inv["item_id"] = pd.to_numeric(df_inv["item_id"], errors="coerce").fillna(0).astype(int)
    df_ses["item_id"] = pd.to_numeric(df_ses["item_id"], errors="coerce").fillna(0).astype(int)

    master_df = load_master()
    df_inv, df_ses, master_df, pending_matches = reconcile_dataframes(df_inv, df_ses, master_df)
    df_inv, df_ses, master_df, decisions = resolve_matches_interactively(df_inv, df_ses, master_df, pending_matches)

    df_inv.to_excel(invoice_path, index=False)
    df_ses.to_excel(session_path, index=False)
    save_master(master_df)
    save_review(decisions)

    approved = sum(1 for d in decisions if d["القرار"].startswith(("موافقة", "تسمية")))
    log.info(f"[مطابقة] اكتمل توحيد الأصناف — {len(decisions)} تطابق عُرض، {approved} اعتُمد")
    return len(decisions)
