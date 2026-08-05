# utils/categorizer.py — v6
# يقرأ خريطة التصنيف من categories.json (مصدر وحيد للأسماء والكلمات المفتاحية).

import os
import re
import json

from utils.logger import get_logger

_ARABIC = r'[\u0600-\u06FF]'
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

    for entry in CATEGORY_ENTRIES:
        whole_word_set = set(entry.get("whole_word_keywords", []))
        for kw in entry.get("keywords", []):
            if kw in whole_word_set:
                if _word_match(kw, text):
                    return entry["main"], entry["sub"]
            else:
                if kw.lower() in text.lower():
                    return entry["main"], entry["sub"]

    hint = category_hint.lower()
    if any(k in hint for k in ["غذائية", "غذاء", "food"]):
        return "مواد غذائية", "أخرى"
    if any(k in hint for k in ["منظف", "تنظيف", "cleaning"]):
        return "منظفات منزلية", "أخرى"
    if any(k in hint for k in ["ورق", "paper"]):
        return "منتجات ورقية", "أخرى"

    return "مواد غذائية", "أخرى"
