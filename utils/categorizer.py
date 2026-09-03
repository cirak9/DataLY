# utils/categorizer.py — v8 محسّن (طريقة معكوسة)
# تقسيم النص للكلمات + فهرس سريع = بحث O(n) بدل O(n²)

import os
import re
import json
from functools import lru_cache
from rapidfuzz import fuzz

from utils.logger import get_logger
from utils import barcode_categories

_ARABIC = r'[؀-ۿ]'
_CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

log = get_logger()


def _load_category_map() -> list:
    with open(_CATEGORIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"[categorizer] تحميل categories.json — الإصدار {data.get('version', '?')}، "
              f"{len(data['categories'])} تصنيف")
    return data["categories"]


CATEGORY_ENTRIES = _load_category_map()

# ============================================================================
# بناء فهرس: كلمة -> (فئة رئيسية، فئة فرعية، محمي؟)
# ============================================================================
_KEYWORD_MAP = {}  # {كلمة_صغيرة: (main, sub, is_protected)}
_ALL_KEYWORDS = []  # [(كلمة_صغيرة, main, sub, is_protected)]

for entry in CATEGORY_ENTRIES:
    whole_word_set = set(entry.get("whole_word_keywords", []))
    for kw in entry.get("keywords", []):
        kw_lower = kw.lower()
        is_protected = kw in whole_word_set
        _KEYWORD_MAP[kw_lower] = (entry["main"], entry["sub"], is_protected)
        _ALL_KEYWORDS.append((kw_lower, entry["main"], entry["sub"], is_protected))


def _word_match(keyword: str, text: str) -> bool:
    """تطابق كلمة كاملة"""
    pattern = r'(?<!' + _ARABIC + r')' + re.escape(keyword) + r'(?!' + _ARABIC + r')'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _extract_words(text: str):
    """استخراج كلمات من النص"""
    # فصل الكلمات بـ spaces والعلامات
    words = re.split(r'\s+|،|\.|-|/', text.lower())
    return [w.strip() for w in words if w.strip()]


@lru_cache(maxsize=5000)
def get_category(item_name: str, category_hint: str = "", sub_hint: str = "", barcode: str = "") -> tuple[str, str]:
    """
    تصنيف سريع — طريقة معكوسة
    بدل البحث عن 61,000 كلمة في النص،
    نقسّم النص لكلمات ونبحث كل كلمة في الفهرس

    ترتيب الأولوية: تصنيف مُعتمَد مسبقًا (sub_hint) > الفهرس المركزي بالباركود (مبني من
    جرد حقيقي عبر كل المتاجر) > تطابق كلمات مفتاحية > تقريبي > تخمين عام.
    """
    if sub_hint and sub_hint not in ("أخرى", "", "nan", "None"):
        return category_hint, sub_hint

    if barcode:
        indexed = barcode_categories.lookup(barcode)
        if indexed:
            return indexed

    text = f"{item_name} {category_hint}".strip()
    text_lower = text.lower()
    text_words = _extract_words(text)

    # ========================================================================
    # المرحلة 1: تطابق دقيق (O(m) حيث m = عدد كلمات النص)
    # ========================================================================
    for text_word in text_words:
        if text_word in _KEYWORD_MAP:
            main, sub, is_protected = _KEYWORD_MAP[text_word]
            if is_protected:
                # للكلمات المحمية، تحقق من word boundary
                for kw_lower, m, s, _ in _ALL_KEYWORDS:
                    if kw_lower == text_word and m == main and s == sub:
                        # استخراج الكلمة الأصلية
                        for entry in CATEGORY_ENTRIES:
                            for kw in entry.get("whole_word_keywords", []):
                                if kw.lower() == kw_lower:
                                    if _word_match(kw, text):
                                        return main, sub
            else:
                # للكلمات العادية
                return main, sub

    # تحقق أيضاً من كلمات مركّبة (كلمتان متتاليتان)
    for i in range(len(text_words) - 1):
        combined = f"{text_words[i]} {text_words[i+1]}"
        if combined in _KEYWORD_MAP:
            main, sub, is_protected = _KEYWORD_MAP[combined]
            return main, sub

    # ========================================================================
    # المرحلة 2: fuzzy محدود جداً (محاولات محدودة فقط)
    # ========================================================================
    best_match = None
    best_score = 0

    # جرّب fuzzy على أول 10 كلمات من النص فقط (بدل جميع الكلمات)
    for text_word in text_words[:10]:
        for kw_lower, main, sub, is_protected in _ALL_KEYWORDS:
            # تخطي الكلمات المحمية والقصيرة
            if is_protected or len(kw_lower) < 4:
                continue

            # تخطي إذا كانت الفروقات كبيرة
            if abs(len(kw_lower) - len(text_word)) > 5:
                continue

            score = fuzz.partial_ratio(kw_lower, text_word)
            # كلمات قصيرة (٤-٥ أحرف) عندها احتمال تشابه عرضي أعلى بكثير (تركيبات محدودة) —
            # اكتُشف فعلياً: "كورن" ≈ "كلور" (منظفات) بـ85.7% رغم أنهما كلمتان مختلفتان
            # كلياً بالمعنى. نطلب تشابهاً أعلى كل ما الكلمة أقصر، بدل حد ثابت 85% للكل.
            min_score = 92 if len(kw_lower) <= 4 else (88 if len(kw_lower) <= 6 else 85)
            if score > best_score and score >= min_score:
                best_score = score
                best_match = (main, sub)

    if best_match:
        return best_match

    # ========================================================================
    # المرحلة 3: افتراضي
    # ========================================================================
    hint = category_hint.lower()
    if any(k in hint for k in ["غذائية", "غذاء", "food"]):
        return "مواد غذائية", "أخرى"
    if any(k in hint for k in ["منظف", "تنظيف", "cleaning"]):
        return "منظفات منزلية", "أخرى"
    if any(k in hint for k in ["ورق", "paper"]):
        return "منتجات ورقية", "أخرى"

    return "مواد غذائية", "أخرى"
