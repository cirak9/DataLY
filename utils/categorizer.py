# utils/categorizer.py — v7
# يقرأ خريطة التصنيف من categories.json (مصدر وحيد للأسماء والكلمات المفتاحية).
# v7: إضافة fuzzy matching للتعرف على أصناف أكثر بدقة

import os
import re
import json
from rapidfuzz import fuzz

from utils.logger import get_logger

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


def _word_match(keyword: str, text: str) -> bool:
    pattern = r'(?<!' + _ARABIC + r')' + re.escape(keyword) + r'(?!' + _ARABIC + r')'
    return bool(re.search(pattern, text, re.IGNORECASE))


def get_category(item_name: str, category_hint: str = "", sub_hint: str = "") -> tuple[str, str]:
    if sub_hint and sub_hint not in ("أخرى", "", "nan", "None"):
        return category_hint, sub_hint

    text = f"{item_name} {category_hint}".strip()

    # المرحلة 1: التطابق الدقيق (Exact Match) — الأولوية الأعلى
    for entry in CATEGORY_ENTRIES:
        whole_word_set = set(entry.get("whole_word_keywords", []))
        for kw in entry.get("keywords", []):
            if kw in whole_word_set:
                if _word_match(kw, text):
                    return entry["main"], entry["sub"]
            else:
                if kw.lower() in text.lower():
                    return entry["main"], entry["sub"]

    # المرحلة 2: التطابق المرن (Fuzzy Match)
    # فقط للكلمات الطويلة وغير محمية بـ whole_word_keywords
    best_match = None
    best_score = 0
    for entry in CATEGORY_ENTRIES:
        whole_word_set = set(entry.get("whole_word_keywords", []))
        for kw in entry.get("keywords", []):
            # تجاهل: كلمات قصيرة OR محمية بـ whole_word_keywords
            if len(kw) < 4 or kw in whole_word_set:
                continue
            score = fuzz.partial_ratio(kw.lower(), text.lower())
            if score > best_score and score >= 80:
                best_score = score
                best_match = entry

    if best_match:
        return best_match["main"], best_match["sub"]

    # المرحلة 3: التصنيف بناءً على hints
    hint = category_hint.lower()
    if any(k in hint for k in ["غذائية", "غذاء", "food"]):
        return "مواد غذائية", "أخرى"
    if any(k in hint for k in ["منظف", "تنظيف", "cleaning"]):
        return "منظفات منزلية", "أخرى"
    if any(k in hint for k in ["ورق", "paper"]):
        return "منتجات ورقية", "أخرى"

    return "مواد غذائية", "أخرى"
