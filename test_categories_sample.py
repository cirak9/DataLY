#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_categories_sample.py — اختبار شامل للتصنيفات مع عينات حقيقية

import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from utils.categorizer import get_category

# ==============================================================================
# 1. عينات البيانات
# ==============================================================================

FOOD_SAMPLES = [
    # أرز وحبوب
    ("أرز بسمتي 5 كجم", "مواد غذائية", "أرز وحبوب"),
    ("قمح كامل 1 كجم", "مواد غذائية", "أرز وحبوب"),
    ("شوفان طبيعي 500 جرام", "مواد غذائية", "أرز وحبوب"),

    # معكرونة
    ("سباغيتي 400 جرام", "مواد غذائية", "معكرونة ومعجنات"),
    ("فتوتشيني 500 جرام", "مواد غذائية", "معكرونة ومعجنات"),

    # توابل
    ("ملح الطعام 500 جرام", "مواد غذائية", "توابل وبهارات"),
    ("فلفل أسود 100 جرام", "مواد غذائية", "توابل وبهارات"),
    ("كمون 200 جرام", "مواد غذائية", "توابل وبهارات"),

    # زيوت
    ("زيت زيتون بكر 500 مل", "مواد غذائية", "زيوت ودهون"),
    ("زيت جوز هند 400 جرام", "مواد غذائية", "زيوت ودهون"),

    # حلويات
    ("سكر أبيض 1 كجم", "مواد غذائية", "السكريات والحلويات"),
    ("عسل نقي 500 جرام", "مواد غذائية", "السكريات والحلويات"),
    ("شيكولاتة داكنة 100 جرام", "مواد غذائية", "السكريات والحلويات"),

    # منتجات ألبان
    ("حليب طازج 1 لتر", "مواد غذائية", "منتجات ألبان"),
    ("لبن زبادي 500 جرام", "مواد غذائية", "منتجات ألبان"),
    ("جبن أبيض 500 جرام", "مواد غذائية", "منتجات ألبان"),

    # مشروبات
    ("قهوة تحميص متوسط 250 جرام", "مواد غذائية", "المشروبات"),
    ("شاي أسود 50 جرام", "مواد غذائية", "المشروبات"),
    ("عصير برتقال 1 لتر", "مواد غذائية", "المشروبات"),

    # مكسرات
    ("لوز كامل 250 جرام", "مواد غذائية", "مكسرات وفواكه مجiffة"),
    ("فستق حلبي 200 جرام", "مواد غذائية", "مكسرات وفواكه مجiffة"),

    # لحوم (الحد الأدنى من الاختبار)
    ("دجاج طازج 1 كجم", "مواد غذائية", "اللحوم والدواجن"),

    # صلصات
    ("صلصة طماطم 400 جرام", "مواد غذائية", "صلصات ومعلبات"),
    ("مايونيز 500 جرام", "مواد غذائية", "صلصات ومعلبات"),
]

CLEANING_SAMPLES = [
    # غسيل ملابس
    ("مسحوق غسيل أوتوماتيك 2 كجم", "منظفات منزلية", "غسيل ملابس"),
    ("سائل غسيل ملابس 1 لتر", "منظفات منزلية", "غسيل ملابس"),
    ("مبيض آمن على الألوان 1 لتر", "منظفات منزلية", "غسيل ملابس"),

    # غسيل أواني
    ("سائل جلي قوي 500 مل", "منظفات منزلية", "غسيل أواني"),
    ("جل الأطباق المركز 1 لتر", "منظفات منزلية", "غسيل أواني"),

    # معقمات
    ("كلور منزلي 1 لتر", "منظفات منزلية", "معقمات"),
    ("معقم الأسطح متعدد الأغراض 500 مل", "منظفات منزلية", "معقمات"),
    ("ديتول سائل 500 مل", "منظفات منزلية", "معقمات"),

    # أرضيات
    ("منظف أرضيات خشبية 1 لتر", "منظفات منزلية", "تنظيف أرضيات"),
    ("منظف أرضيات سيراميك 500 مل", "منظفات منزلية", "تنظيف أرضيات"),

    # زجاج
    ("منظف زجاج بدون شرائط 500 مل", "منظفات منزلية", "تنظيف زجاج"),
    ("منظف النوافذ اللامع 250 مل", "منظفات منزلية", "تنظيف زجاج"),

    # معطرات
    ("معطر جو بالورد 300 مل", "منظفات منزلية", "معطرات"),
    ("بخاخ الجو برائحة الليمون 200 مل", "منظفات منزلية", "معطرات"),

    # أدوات
    ("إسفنجة تنظيف 3 حبات", "منظفات منزلية", "أدوات تنظيف"),
    ("فرشاة تنظيف مختلفة الأحجام 5 حبات", "منظفات منزلية", "أدوات تنظيف"),
]

EDGE_CASES = [
    # حالات تحديث
    ("كريم اليد 100 مل", "عناية شخصية", "عناية بالجسم"),
    ("ماسك الشعر 200 مل", "عناية شخصية", "عناية بالشعر"),
    ("معجون أسنان 75 مل", "عناية شخصية", "عناية بالفم"),
]

# ==============================================================================
# 2. دوال الاختبار
# ==============================================================================

def test_sample(product_name, expected_main, expected_sub):
    """اختبار صنف واحد"""
    actual_main, actual_sub = get_category(product_name)

    main_ok = actual_main == expected_main
    sub_ok = actual_sub == expected_sub
    overall_ok = main_ok and sub_ok

    status = "✓" if overall_ok else "✗"

    return {
        "product": product_name,
        "expected_main": expected_main,
        "expected_sub": expected_sub,
        "actual_main": actual_main,
        "actual_sub": actual_sub,
        "main_ok": main_ok,
        "sub_ok": sub_ok,
        "overall_ok": overall_ok,
        "status": status
    }


def run_tests(samples, category_name):
    """تشغيل مجموعة اختبارات"""
    print(f"\n{'='*80}")
    print(f"{category_name}")
    print(f"{'='*80}")

    results = []
    start_time = time.time()

    for product, expected_main, expected_sub in samples:
        result = test_sample(product, expected_main, expected_sub)
        results.append(result)

        # طباعة النتيجة
        status = result['status']
        print(f"{status} {product[:50]:<50} → {result['actual_main']} / {result['actual_sub']}")

        # تفاصيل إذا كان هناك خطأ
        if not result['overall_ok']:
            if not result['main_ok']:
                print(f"  ✗ الفئة الرئيسية: توقع '{result['expected_main']}' لكن حصلت على '{result['actual_main']}'")
            if not result['sub_ok']:
                print(f"  ✗ الفئة الفرعية: توقع '{result['expected_sub']}' لكن حصلت على '{result['actual_sub']}'")

    elapsed = time.time() - start_time
    passed = sum(1 for r in results if r['overall_ok'])
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n{category_name} — النتائج:")
    print(f"  النجاحات: {passed}/{total} ({success_rate:.1f}%)")
    print(f"  الوقت: {elapsed:.2f} ثانية")

    return results, success_rate


# ==============================================================================
# 3. التنفيذ
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("اختبار التصنيفات مع عينات البيانات الحقيقية")
    print("="*80)

    all_results = []
    all_scores = []

    # اختبار المنتجات الغذائية
    food_results, food_score = run_tests(FOOD_SAMPLES, "المنتجات الغذائية")
    all_results.extend(food_results)
    all_scores.append(food_score)

    # اختبار مواد التنظيف
    cleaning_results, cleaning_score = run_tests(CLEANING_SAMPLES, "مواد التنظيف")
    all_results.extend(cleaning_results)
    all_scores.append(cleaning_score)

    # اختبار الحالات الخاصة
    edge_results, edge_score = run_tests(EDGE_CASES, "الحالات الخاصة")
    all_results.extend(edge_results)
    all_scores.append(edge_score)

    # الملخص الشامل
    print(f"\n{'='*80}")
    print("الملخص الشامل")
    print(f"{'='*80}")

    total_passed = sum(1 for r in all_results if r['overall_ok'])
    total_tests = len(all_results)
    overall_score = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\nإجمالي الاختبارات: {total_tests}")
    print(f"النجاحات: {total_passed}")
    print(f"الأخطاء: {total_tests - total_passed}")
    print(f"معدل النجاح: {overall_score:.1f}%")

    print(f"\nتفصيل النتائج حسب الفئة:")
    print(f"  • المنتجات الغذائية: {food_score:.1f}%")
    print(f"  • مواد التنظيف: {cleaning_score:.1f}%")
    print(f"  • الحالات الخاصة: {edge_score:.1f}%")

    print(f"\n{'='*80}\n")

    # عرض الأخطاء فقط
    errors = [r for r in all_results if not r['overall_ok']]
    if errors:
        print("الأخطاء المكتشفة:")
        print(f"{'='*80}")
        for error in errors:
            print(f"\n✗ {error['product']}")
            print(f"  المتوقع: {error['expected_main']} > {error['expected_sub']}")
            print(f"  الفعلي:  {error['actual_main']} > {error['actual_sub']}")
        print(f"\n{'='*80}\n")
    else:
        print("✓ جميع الاختبارات نجحت بنسبة 100%!\n")
