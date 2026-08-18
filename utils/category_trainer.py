# utils/category_trainer.py — أداة تدريب وتحليل التصنيفات
# تساعد على اكتشاف أصناف جديدة والكلمات المفتاحية الناقصة

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

import json
from collections import Counter
from utils.categorizer import get_category, CATEGORY_ENTRIES
from utils.logger import get_logger

log = get_logger()


def analyze_uncategorized_items(items: list[str]) -> dict:
    """تحليل الأصناف غير المصنفة أو المصنفة بـ 'أخرى'"""
    uncategorized = {}

    for item in items:
        main, sub = get_category(item)
        if sub == "أخرى":
            if main not in uncategorized:
                uncategorized[main] = []
            uncategorized[main].append(item)

    return uncategorized


def extract_keywords_from_items(items: list[str], min_frequency: int = 2) -> dict[str, list]:
    """استخراج كلمات مفتاحية متكررة من قائمة أصناف"""
    # فصل الكلمات من جميع الأصناف
    word_freq = Counter()

    for item in items:
        words = item.split()
        for word in words:
            word_clean = word.strip("،.؛:-()").lower()
            if len(word_clean) >= 3:  # تجاهل كلمات قصيرة جداً
                word_freq[word_clean] += 1

    # ترشيح الكلمات المتكررة
    suggested_keywords = {}
    for word, count in word_freq.most_common(50):
        if count >= min_frequency:
            suggested_keywords[word] = count

    return suggested_keywords


def suggest_new_keywords() -> None:
    """اقتراح كلمات مفتاحية جديدة من نقاط الضعف المكتشفة"""

    print("\n" + "="*60)
    print("تحليل التصنيفات — اقتراحات لتحسين النظام")
    print("="*60)

    # اختبار عينة من الأصناف الشائعة
    test_items = [
        "زيت زيتون بكر 500 مل",
        "صلصة سويا 200 مل",
        "دبس التمر 400 جرام",
        "طحينة سمسم 400 جرام",
        "أرز بسمتي فاخر 5 كجم",
        "قمح كامل حبة 1 كجم",
        "شوفان 500 جرام",
        "فشار 200 جرام",
        "حبوب الفطور (كورن فليكس) 350 جرام",
        "الزبيب 250 جرام",
        "التمر هندي 250 جرام",
        "جوز الهند 200 جرام",
        "لوز 250 جرام",
        "فستق 300 جرام",
        "شكولاتة 100 جرام",
        "منظف سيراميك 1 لتر",
        "معطر أرضيات 500 مل",
        "مزيل الرائحة 150 مل",
        "كريم اليد 100 مل",
        "ماسك الشعر 200 مل"
    ]

    print("\nنتائج التصنيف:")
    print("-" * 60)

    category_coverage = {}
    for item in test_items:
        main, sub = get_category(item)
        key = f"{main} > {sub}"
        if key not in category_coverage:
            category_coverage[key] = []
        category_coverage[key].append(item)

    for category, items_list in sorted(category_coverage.items()):
        status = "[OK]" if "أخرى" not in category else "[*]"
        print(f"{status} {category}: {len(items_list)} صنف")
        if "أخرى" in category:
            for item in items_list:
                print(f"    - {item}")

    print("\n" + "="*60)
    print("الكلمات المفتاحية الموصى بإضافتها:")
    print("="*60)

    suggested = extract_keywords_from_items(test_items)

    # مقارنة مع الكلمات الموجودة
    existing_keywords = set()
    for entry in CATEGORY_ENTRIES:
        existing_keywords.update(entry.get("keywords", []))

    new_keywords = {w: c for w, c in suggested.items() if w not in existing_keywords}

    if new_keywords:
        for word, count in sorted(new_keywords.items(), key=lambda x: x[1], reverse=True):
            print(f"  + {word} (يظهر {count}x)")
    else:
        print("  OK: معظم الكلمات المفتاحية موجودة بالفعل!")

    print("="*60 + "\n")


if __name__ == "__main__":
    suggest_new_keywords()
