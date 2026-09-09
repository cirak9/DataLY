# منقول من session/session_generator.py بالأداة الأصلية (كانت دوال محلية متداخلة
# جوا generate_session_files قبل الرسملة هون كدوال مستقلة تقبل صف واحد dict-like) —
# نفس المنطق حرفياً، راجع docs/REBUILD_PLAN.md قسم 2. المهم: per_box يرجّع None صراحة
# لو غير معروف — ممنوع نفبرك 1 (بق حقيقي انصلح بالأداة الأصلية هالجلسة، NaN/None truthy
# ببايثون فأي "or 1" ساذج يخفي القيمة الفاضية الحقيقية).
import re

_PER_BOX_WITH_WORD = re.compile(r"(?:كرتون|صندوق|كرتونة|بالة|جوال|شيكارة)\D{0,4}(\d+)")
_PER_BOX_PARENS = re.compile(r"\((\d+)")
_PER_BOX_BARE_NUMBER = re.compile(r"^\d+$")


def extract_per_box_from_unit(unit) -> int | None:
    text = str(unit).strip()
    match = _PER_BOX_WITH_WORD.search(text) or _PER_BOX_PARENS.search(text)
    if match:
        return int(match.group(1))
    if _PER_BOX_BARE_NUMBER.match(text):
        return int(text)
    return None


def calc_per_box(row: dict) -> int | None:
    pb = float(row.get("per_box", 0) or 0)
    if pb > 1:
        return int(pb)
    return extract_per_box_from_unit(row.get("unit", ""))


def _apply_discount(price: float, row: dict) -> float:
    disc = float(row.get("discount_pct", 0) or 0)
    return round(price * (1 - disc), 3)


def calc_unit_cost(row: dict) -> float:
    try:
        # الكمية بالفاتورة = عدد قطع مفردة أصلًا، مو عدد صناديق — بدون ضرب بعدد القطع بالعبوة.
        total_units = float(row.get("boxes", 0) or 0)
        total_p = _apply_discount(float(row.get("total_price", 0) or 0), row)
        cost_p = _apply_discount(float(row.get("cost_price", 0) or 0), row)
        if total_p > 0 and total_units > 0:
            return round(total_p / total_units, 3)
        if cost_p > 0:
            return round(cost_p, 3)
        return 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def calc_total(row: dict) -> float:
    try:
        total_p = _apply_discount(float(row.get("total_price", 0) or 0), row)
        if total_p > 0:
            return round(total_p, 3)
        boxes = float(row.get("boxes", 0) or 0)
        cost_p = _apply_discount(float(row.get("cost_price", 0) or 0), row)
        if boxes > 0 and cost_p > 0:
            return round(boxes * cost_p, 3)
        return 0.0
    except (TypeError, ValueError):
        return 0.0
