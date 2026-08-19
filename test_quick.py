#!/usr/bin/env python
# -*- coding: utf-8 -*-
# اختبار سريع

import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from utils.categorizer import get_category

# اختبارات بسيطة
tests = [
    ("أرز أبيض 5 كجم", "مواد غذائية", "أرز وحبوب"),
    ("مسحوق غسيل 2 كجم", "منظفات منزلية", "غسيل ملابس"),
    ("سائل جلي 1 لتر", "منظفات منزلية", "غسيل أواني"),
    ("عسل نقي 500 جرام", "مواد غذائية", "مربيات وعسل"),
]

print("\nاختبار سريع:")
print("="*60)

start = time.time()
passed = 0

for product, exp_main, exp_sub in tests:
    actual_main, actual_sub = get_category(product)
    ok = (actual_main == exp_main and actual_sub == exp_sub)
    status = "✓" if ok else "✗"
    if ok:
        passed += 1
    print(f"{status} {product:<30} → {actual_main}/{actual_sub}")
    if not ok:
        print(f"  المتوقع: {exp_main}/{exp_sub}")

elapsed = time.time() - start
print(f"\nالنتائج: {passed}/{len(tests)} ({passed*100//len(tests)}%)")
print(f"الوقت: {elapsed:.2f} ثانية")
print("="*60 + "\n")
