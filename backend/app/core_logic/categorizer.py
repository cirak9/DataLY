# منقول شبه حرفي من utils/categorizer.py بالأداة الأصلية (خوارزمية "الطريقة المعكوسة":
# فهرس كلمة→تصنيف مبني مرة وحدة، بدل بحث كل كلمة مفتاحية بكل النص). راجع
# docs/REBUILD_PLAN.md قسم 2. الفرق الوحيد عن الأصل: هذا الملف نسخة "نقية" بدون اعتماد
# على فهرس الباركود (كان utils/barcode_categories.py، صار DB فعلياً) — أولوية الباركود
# وتحويل (رئيسي, فرعي) لـcategory_id صارت بـapp/services/catalog_service.py اللي عنده
# اتصال قاعدة بيانات؛ هالملف يبقى دالة نصية بحتة (نص → رئيسي/فرعي) بدون DB إطلاقاً،
# قابلة للاختبار والـcaching بمعزل عن أي اتصال، بالضبط زي الأصل.
import json
import os
import re
from functools import lru_cache

from rapidfuzz import fuzz

_ARABIC = r"[؀-ۿ]"
_CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories_seed.json")


def _load_category_map() -> list:
    with open(_CATEGORIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


CATEGORY_ENTRIES = _load_category_map()

_KEYWORD_MAP = {}
_ALL_KEYWORDS = []

for entry in CATEGORY_ENTRIES:
    whole_word_set = set(entry.get("whole_word_keywords", []))
    for kw in entry.get("keywords", []):
        kw_lower = kw.lower()
        is_protected = kw in whole_word_set
        _KEYWORD_MAP[kw_lower] = (entry["main"], entry["sub"], is_protected)
        _ALL_KEYWORDS.append((kw_lower, entry["main"], entry["sub"], is_protected))


def _word_match(keyword: str, text: str) -> bool:
    pattern = r"(?<!" + _ARABIC + r")" + re.escape(keyword) + r"(?!" + _ARABIC + r")"
    return bool(re.search(pattern, text, re.IGNORECASE))


def _extract_words(text: str):
    words = re.split(r"\s+|،|\.|-|/", text.lower())
    return [w.strip() for w in words if w.strip()]


@lru_cache(maxsize=5000)
def get_category_by_name(item_name: str, category_hint: str = "", sub_hint: str = "") -> tuple[str, str]:
    """
    تصنيف من الاسم بس (بدون باركود — أولوية الباركود صارت بـcatalog_service.get_category_id،
    اللي عنده اتصال قاعدة بيانات لفهرس product_catalog). ترتيب الأولوية: تصنيف مُعتمَد
    مسبقًا (sub_hint) > تطابق كلمات مفتاحية > تقريبي > تخمين عام.
    """
    if sub_hint and sub_hint not in ("أخرى", "", "nan", "None"):
        return category_hint, sub_hint

    text = f"{item_name} {category_hint}".strip()
    text_words = _extract_words(text)

    # المرحلة 1: تطابق دقيق
    for text_word in text_words:
        if text_word in _KEYWORD_MAP:
            main, sub, is_protected = _KEYWORD_MAP[text_word]
            if is_protected:
                for kw_lower, m, s, _ in _ALL_KEYWORDS:
                    if kw_lower == text_word and m == main and s == sub:
                        for entry in CATEGORY_ENTRIES:
                            for kw in entry.get("whole_word_keywords", []):
                                if kw.lower() == kw_lower:
                                    if _word_match(kw, text):
                                        return main, sub
            else:
                return main, sub

    for i in range(len(text_words) - 1):
        combined = f"{text_words[i]} {text_words[i + 1]}"
        if combined in _KEYWORD_MAP:
            main, sub, is_protected = _KEYWORD_MAP[combined]
            return main, sub

    # المرحلة 2: fuzzy محدود
    best_match = None
    best_score = 0
    for text_word in text_words[:10]:
        for kw_lower, main, sub, is_protected in _ALL_KEYWORDS:
            if is_protected or len(kw_lower) < 4:
                continue
            if abs(len(kw_lower) - len(text_word)) > 5:
                continue
            score = fuzz.partial_ratio(kw_lower, text_word)
            # كلمات قصيرة (٤-٦ أحرف) عندها احتمال تشابه عرضي أعلى بكثير — اكتُشف فعلياً:
            # "كورن" ≈ "كلور" بـ85.7% رغم أنهما كلمتان مختلفتان كلياً. حد أعلى كل ما الكلمة أقصر.
            min_score = 92 if len(kw_lower) <= 4 else (88 if len(kw_lower) <= 6 else 85)
            if score > best_score and score >= min_score:
                best_score = score
                best_match = (main, sub)

    if best_match:
        return best_match

    # المرحلة 3: افتراضي
    hint = category_hint.lower()
    if any(k in hint for k in ["غذائية", "غذاء", "food"]):
        return "مواد غذائية", "أخرى"
    if any(k in hint for k in ["منظف", "تنظيف", "cleaning"]):
        return "منظفات منزلية", "أخرى"
    if any(k in hint for k in ["ورق", "paper"]):
        return "منتجات ورقية", "أخرى"

    return "مواد غذائية", "أخرى"
