"""
منطق نصي بحت لتفسير رد Claude Vision — بلا أي اتصال شبكة أو قاعدة بيانات، عشان
يُختبر بمعزل بأمثلة ردود جاهزة. استدعاء الـAPI نفسه بـservices/ocr_service.py.
"""
import json
import re

REQUIRED_FIELDS = {"item_name", "quantity", "unit_cost"}
VALID_CONFIDENCE = {"high", "medium", "low"}

PROMPT = """هذي صورة أو أكثر لفاتورة مورد لمتجر بقالة. استخرج كل صنف مذكور كمصفوفة JSON فقط
(بدون أي نص أو markdown قبلها أو بعدها)، بالشكل:
[{"source_image": 1, "item_name": "...", "quantity": 12, "unit_cost": 8.75, "barcode": "6221031202019", "confidence": "high"}]

قواعد:
- quantity هو عدد القطع المفردة، مو عدد الصناديق/الكراتين — لو الفاتورة مكتوب فيها
  "12 كرتون × 24 قطعة" رجّع 288.
- unit_cost سعر القطعة المفردة الواحدة، مو سعر الكرتون.
- barcode فقط لو واضح ومطبوع بالفاتورة، غير هيك اجعله null.
- confidence: "high" لو النص واضح ومقروء تماماً، "medium" لو فيه غموض بسيط، "low" لو
  الخط غير واضح أو مقصوص أو يحتاج تدقيق بشري دقيق.
- source_image رقم الصورة اللي الصنف مستخرَج منها (1 للصورة الأولى، 2 للثانية...).
- رجّع فقط مصفوفة JSON صحيحة التركيب، بلا أي شرح."""


class OcrParseError(Exception):
    pass


def parse_extraction_response(text: str) -> list[dict]:
    """
    يحوّل رد النموذج النصي إلى قائمة قواميس مُتحقَّق منها. يرمي OcrParseError برسالة
    عربية واضحة لو الرد مو JSON صالح أو ناقص حقول أساسية — بدل ما يمرّر بيانات مشوّهة
    للطبقة اللي فوق بصمت.
    """
    match = re.search(r"\[.*\]", text.strip(), re.DOTALL)
    if not match:
        raise OcrParseError("رد النموذج ما فيه مصفوفة JSON — جرّب صور أوضح")

    try:
        raw_items = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise OcrParseError(f"رد النموذج JSON غير صالح: {e}") from e

    if not isinstance(raw_items, list):
        raise OcrParseError("رد النموذج مو مصفوفة")

    items: list[dict] = []
    for i, raw in enumerate(raw_items):
        if not isinstance(raw, dict) or not REQUIRED_FIELDS.issubset(raw):
            raise OcrParseError(f"الصنف رقم {i + 1} بالرد ناقص حقول أساسية")

        confidence = raw.get("confidence")
        if confidence not in VALID_CONFIDENCE:
            confidence = "medium"

        items.append(
            {
                "source_image": int(raw.get("source_image") or 1),
                "item_name": str(raw["item_name"]).strip(),
                "quantity": float(raw["quantity"]),
                "unit_cost": float(raw["unit_cost"]),
                "barcode": (str(raw["barcode"]).strip() or None) if raw.get("barcode") else None,
                "confidence": confidence,
            }
        )
    return items
