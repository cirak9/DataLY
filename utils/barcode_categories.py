# utils/barcode_categories.py
# فهرس تصنيف مركزي {باركود -> تصنيف رئيسي/فرعي}، يتراكم من كل ملف master_items.xlsx
# (أو جرد مخزون مستقل) تتم معالجته لأي متجر — عبر كل المتاجر، لا متجر واحد بس. مصدر
# أدق من التخمين بالكلمات المفتاحية (categories.json) لأنه مبني على تصنيف حقيقي مؤكد
# من بيانات جرد فعلية، وقيمته تتراكم بمرور الوقت وعدد المتاجر — مو مرتبط بفاتورة وحدة.
#
# ملاحظة مهمة: هذا غير قرار "master_items.xlsx للقراءة فقط بلا حفظ" — ذاك القرار عن
# عدم تراكم قائمة أصناف متجر واحد من جلسات فواتيره (راجع ARCHITECTURE.md). هذا الفهرس
# أصل بيانات منفصل ومقصود تراكمه، يخص التصنيف فقط، ويخدم كل المتاجر مع بعض.
import os
import json
from datetime import date
from utils.logger import get_logger

log = get_logger()

_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "barcode_categories.json")
_IGNORED_SUB = ("", "أخرى", "nan", "none")

_cache = None  # يُحمَّل مرة وحدة بالذاكرة، يُكتب للقرص عند كل تحديث فعلي بس


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.exists(_INDEX_PATH):
        _cache = {}
        return _cache
    try:
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache = data.get("index", {})
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"[فهرس التصنيف] تعذّرت قراءة {_INDEX_PATH}: {e} — بدء فهرس فاضي")
        _cache = {}
    return _cache


def _save() -> None:
    os.makedirs(os.path.dirname(_INDEX_PATH), exist_ok=True)
    with open(_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "index": _cache}, f, ensure_ascii=False, indent=2)


def lookup(barcode: str):
    """يرجّع (رئيسي, فرعي) لو الباركود معروف بالفهرس، وإلا None."""
    barcode = str(barcode).strip()
    if not barcode or barcode.lower() == "nan":
        return None
    entry = _load().get(barcode)
    if not entry:
        return None
    return entry["main"], entry["sub"]


def main_for_sub(sub: str):
    """يرجّع التصنيف الرئيسي المعتمد لتصنيف فرعي معيّن لو سبق وتعلّمه الفهرس (من أي متجر
    أو ملف)، وإلا None. يخدم حالة ملفات الجرد اللي فيها عمود تصنيف فرعي بس بدون رئيسي —
    لو الفرعي معروف مسبقًا بالفهرس، رئيسيه المعتمد يُعاد استخدامه بدل تخمينه من جديد."""
    sub = str(sub).strip()
    if not sub or sub.lower() in _IGNORED_SUB:
        return None
    for entry in _load().values():
        if entry["sub"] == sub:
            return entry["main"]
    return None


def _upsert(barcode, main, sub, name, store_id) -> bool:
    """تسجيل/تحديث صنف واحد بالذاكرة بس (بدون كتابة قرص) — الأحدث يربح عند التعارض.
    يرجّع True لو فعليًا كان فيه باركود وتصنيف صالحين يستاهلون التسجيل."""
    barcode = str(barcode).strip()
    main = str(main).strip()
    sub = str(sub).strip()
    if not barcode or barcode.lower() == "nan" or not main or sub.lower() in _IGNORED_SUB:
        return False
    _load()[barcode] = {
        "name": str(name).strip(),
        "main": main,
        "sub": sub,
        "source_store": store_id or "",
        "updated_at": date.today().isoformat(),
    }
    return True


def learn(barcode: str, main: str, sub: str, name: str = "", store_id: str = "") -> bool:
    """تسجيل صنف واحد وحفظه فورًا — للاستخدام المباشر خارج جدول كامل."""
    changed = _upsert(barcode, main, sub, name, store_id)
    if changed:
        _save()
    return changed


def learn_from_dataframe(df, barcode_col: str, main_col: str, sub_col: str,
                          name_col: str = None, store_id: str = "") -> int:
    """يغذّي الفهرس من أي جدول فيه أعمدة باركود/تصنيف رئيسي/تصنيف فرعي — زي master_items.xlsx
    (يُستدعى تلقائيًا وقت كل --merge) أو ملف جرد مستقل. صفوف بلا باركود أو بتصنيف فرعي
    "أخرى"/فاضي تُتجاهَل بصمت (ما فيها معلومة تستاهل التسجيل). يرجّع عدد الأصناف اللي
    فعليًا انسجلت أو اتحدّثت."""
    learned = 0
    for _, row in df.iterrows():
        name = row.get(name_col, "") if name_col else ""
        if _upsert(row.get(barcode_col, ""), row.get(main_col, ""), row.get(sub_col, ""), name, store_id):
            learned += 1
    if learned:
        _save()
        log.info(f"[فهرس التصنيف] اتعلّم/تحدّث {learned} صنف بالفهرس المركزي (من {store_id or 'مصدر بدون متجر محدد'})")
    return learned


def learn_many(records) -> int:
    """نفس learn() لكن لعدة أصناف دفعة وحدة — حفظ قرص مرة وحدة بس بنهاية الدفعة (بدل
    حفظ مستقل لكل صنف زي learn()). كل عنصر بـrecords: (barcode, main, sub, name, store_id)."""
    learned = 0
    for barcode, main, sub, name, store_id in records:
        if _upsert(barcode, main, sub, name, store_id):
            learned += 1
    if learned:
        _save()
    return learned
