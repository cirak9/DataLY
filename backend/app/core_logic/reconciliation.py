# منقول شبه حرفي من fusion/reconciliation.py بالأداة الأصلية — منطق مقارنة الحجم/الوزن
# بين اسمين، بمعزل تام عن أي DB أو ملف. راجع docs/REBUILD_PLAN.md قسم 2.
import re

# باركود مطابق لكن الاسم مختلف عن كذا → "تنبيه" يُعرض مع التطابق المُقترَح وقت طلب الموافقة
# (مو رفض تلقائي — كل تطابق بالباركود يُعرض للموافقة بغض النظر عن هذا الحد). الحد منخفض
# عمدًا: الباركود نفسه دليل هوية قوي، فنفس الصنف قد يُكتب بصيغ عربية مختلفة كثيرًا.
CONFLICT_THRESHOLD = 45
# لا يوجد باركود بالفاتورة → يُقترَح تطابق بالاسم التقريبي (وينتظر موافقة بردو) فقط لو
# التشابه ≥ كذا؛ أقل من كذا يُعتبر "بلا مطابقة معروفة" ولا يُقترَح إطلاقًا. الحد أعلى من
# CONFLICT_THRESHOLD لأنه بدون باركود لا يوجد مرساة هوية، فنطلب ثقة أعلى قبل حتى الاقتراح.
FUZZY_MATCH_THRESHOLD = 60

# WRatio يقيس تشابه النص الكلي بس — "سكر ناعم 10 كجم" و"سكر التميز 1 كغ" يطلعوا متشابهين
# نصيًا رغم إن الحجم مختلف كليًا (10 أضعاف). هذا فرق حجم حقيقي غالبًا يدل على باركود
# مُدخل غلط لعبوة مختلفة، مو مجرد صياغة مختلفة — فنقارن الوزن/الحجم المستخرج كفحص إضافي.
_WEIGHT_UNITS = {"كجم": 1000, "كغ": 1000, "كيلوجرام": 1000, "كيلو": 1000,
                 "جرام": 1, "غرام": 1, "جم": 1, "غم": 1, "غ": 1}
_VOLUME_UNITS = {"لتر": 1000, "لترات": 1000, "مل": 1, "مليلتر": 1}
_SIZE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" +
    "|".join(sorted({**_WEIGHT_UNITS, **_VOLUME_UNITS}, key=len, reverse=True)) +
    r")\b"
)
# فرق الحجم المسموح بيه قبل ما يُعتبر تعارض — يتحمّل فروقات تعبئة بسيطة (900غ مقابل 1كجم)
# لكن يلتقط فرق حجم حقيقي (10كجم مقابل 1كجم).
SIZE_MISMATCH_RATIO = 1.3


def extract_size(name: str):
    """يستخرج (القيمة بوحدة أساسية، الفئة) من اسم الصنف — وزن بالغرام أو حجم بالمليلتر.
    يرجع None لو ما لقى وحدة وزن/حجم معروفة."""
    match = _SIZE_PATTERN.search(name)
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2)
    if unit in _WEIGHT_UNITS:
        return value * _WEIGHT_UNITS[unit], "weight"
    return value * _VOLUME_UNITS[unit], "volume"


def size_conflict_reason(name_a: str, name_b: str) -> str:
    """يرجع سبب تعارض الحجم/الوزن لو موجود، أو "" لو ما فيه تعارض. غموض أو تعذّر
    استخراج حجم من أحد الاسمين = بلا تعارض (نعتمد عندها على WRatio وحده)."""
    size_a, size_b = extract_size(name_a), extract_size(name_b)
    if not size_a or not size_b:
        return ""
    val_a, cat_a = size_a
    val_b, cat_b = size_b
    if cat_a != cat_b:
        return "نوع القياس نفسه مختلف بين الاسمين (وزن مقابل حجم) — راجع يدويًا للتأكد إنه نفس الصنف"
    if val_a and val_b and max(val_a, val_b) / min(val_a, val_b) >= SIZE_MISMATCH_RATIO:
        return "الحجم/الوزن مختلف كليًا (مو مجرد صياغة مختلفة)"
    return ""
