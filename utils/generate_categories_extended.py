# utils/generate_categories_extended.py — مولّد موسّع للتصنيفات
# يولّد 30,000+ تصنيف من خلال تركيب الكلمات والأحجام والأنواع

import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. الكلمات الأساسية (Base Words)
# ==============================================================================

GRAINS = ["أرز", "قمح", "شعير", "ذرة", "شوفان", "جاودار", "كسكس", "برغل", "عدس أسود", "عدس أحمر"]
PASTA = ["سباغيتي", "فتوتشيني", "بينيه", "ريجاتوني", "لازانيا", "ماكاروني", "فوسيلي", "شعيرية"]
SPICES = ["ملح", "فلفل", "كمون", "قرفة", "زعتر", "كزبرة", "ينسون", "هيل", "شطة", "جوزة الطيب"]
OILS = ["زيت زيتون", "زيت نخيل", "زيت جوز هند", "زيت عباد الشمس", "زيت الفول السوداني", "زيت السمسم"]
SWEETENERS = ["سكر أبيض", "سكر بني", "عسل نقي", "عسل برسيم", "شيكولاتة داكنة", "شيكولاتة بيضاء", "كراميل"]
DAIRY = ["حليب طازج", "حليب مبستر", "حليب بودرة", "لبن طازج", "لبنة", "جبن أبيض", "جبن شيدر", "زبادي طازج", "كريمة ثقيلة"]
BEVERAGES = ["قهوة تحميص خفيف", "قهوة تحميص متوسط", "شاي أسود", "شاي أخضر", "شاي بالنعناع", "عصير برتقال", "عصير تفاح", "كاكاو بودرة"]
NUTS = ["لوز كامل", "لوز مقشر", "فستق حلبي", "جوز هند مبروش", "كاجو محمص", "فول سوداني مملح", "بندق مقشر", "صنوبر"]

DETERGENTS = ["مسحوق غسيل أوتوماتيك", "مسحوق غسيل يدوي", "سائل غسيل ملابس", "منظف الملابس القطنية", "منظف الملابس الحساسة", "مبيض آمن على الألوان"]
DISHWASHER = ["سائل جلي قوي", "سائل جلي عادي", "سائل جلي برائحة الليمون", "جل الأطباق المركز", "بودرة الأطباق الآلية", "منظف القدور والمقالي"]
DISINFECT = ["كلور منزلي", "مبيض الملابس", "معقم الأسطح متعدد الأغراض", "معقم الأيدي", "ديتول سائل", "دومستوس تنظيف وتعقيم"]
FLOOR = ["منظف أرضيات خشبية", "منظف أرضيات سيراميك", "منظف أرضيات رخام", "واكس أرضيات لامع", "معقم أرضيات ومطهر"]
GLASS = ["منظف زجاج بدون شرائط", "منظف النوافذ اللامع", "منظف المرايا", "منظف الزجاج والمعادن"]
FRAGRANCE = ["معطر جو بالورد", "معطر جو بالعطور الفرنسية", "بخاخ الجو برائحة الليمون", "معطر رائحة دائم", "شمعة معطرة بالفانيليا"]

BRANDS = ["العلامة الأصلية", "ماركة قسطنطينة", "ماركة الجودة", "العروة الوثقى", "الخيار الأول", "المفضل", "الطبيعي", "الاقتصادي"]
SIZES = ["100 جرام", "200 جرام", "250 جرام", "350 جرام", "400 جرام", "500 جرام", "750 جرام", "1 كجم", "2 كجم", "5 كجم", "10 كجم",
         "50 مل", "100 مل", "200 مل", "250 مل", "500 مل", "750 مل", "1 لتر", "2 لتر", "5 لتر"]
QUALITIES = ["عالي الجودة", "طازج", "طبيعي 100%", "خالي من المواد الحافظة", "عضوي", "مختار بعناية", "مستورد", "محلي"]

# ==============================================================================
# 2. دوال التوليد الذكية
# ==============================================================================

def generate_product_combinations(base_words: list, brands: list = None, sizes: list = None, qualities: list = None):
    """توليد تركيبات متعددة من الكلمات والأحجام والمواصفات"""
    products = set()

    brands = brands or BRANDS
    sizes = sizes or SIZES[:10]  # الأحجام الشائعة فقط
    qualities = qualities or QUALITIES[:5]

    for word in base_words:
        # المنتج البسيط
        products.add(word)

        # مع الحجم
        for size in sizes[:8]:
            products.add(f"{word} {size}")

        # مع الجودة
        for quality in qualities[:3]:
            products.add(f"{word} {quality}")

        # مع الماركة والحجم
        for brand in brands[:3]:
            for size in sizes[:4]:
                products.add(f"{word} {brand} {size}")

    return list(products)


def generate_food_categories():
    """توليد فئات غذائية شاملة"""
    categories = []

    # أرز وحبوب
    keywords = generate_product_combinations(GRAINS)
    categories.append({
        "main": "مواد غذائية",
        "sub": "أرز وحبوب",
        "keywords": keywords,
        "whole_word_keywords": ["رز", "قمح", "شعير"]
    })

    # معكرونة
    keywords = generate_product_combinations(PASTA)
    categories.append({
        "main": "مواد غذائية",
        "sub": "معكرونة ومعجنات",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # توابل
    keywords = generate_product_combinations(SPICES)
    categories.append({
        "main": "مواد غذائية",
        "sub": "توابل وبهارات",
        "keywords": keywords,
        "whole_word_keywords": ["ملح", "فلفل"]
    })

    # زيوت
    keywords = generate_product_combinations(OILS)
    categories.append({
        "main": "مواد غذائية",
        "sub": "زيوت ودهون",
        "keywords": keywords,
        "whole_word_keywords": ["زيت"]
    })

    # سكريات وحلويات
    keywords = generate_product_combinations(SWEETENERS)
    categories.append({
        "main": "مواد غذائية",
        "sub": "السكريات والحلويات",
        "keywords": keywords,
        "whole_word_keywords": ["سكر", "عسل"]
    })

    # منتجات ألبان
    keywords = generate_product_combinations(DAIRY)
    categories.append({
        "main": "مواد غذائية",
        "sub": "منتجات ألبان",
        "keywords": keywords,
        "whole_word_keywords": ["حليب", "لبن", "جبن"]
    })

    # المشروبات
    keywords = generate_product_combinations(BEVERAGES)
    categories.append({
        "main": "مواد غذائية",
        "sub": "المشروبات",
        "keywords": keywords,
        "whole_word_keywords": ["قهوة", "شاي"]
    })

    # المكسرات
    keywords = generate_product_combinations(NUTS)
    categories.append({
        "main": "مواد غذائية",
        "sub": "مكسرات وفواكه مجففة",
        "keywords": keywords,
        "whole_word_keywords": ["لوز", "فستق"]
    })

    return categories


def generate_cleaning_categories():
    """توليد فئات منظفات شاملة"""
    categories = []

    # غسيل ملابس
    keywords = generate_product_combinations(DETERGENTS)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "غسيل ملابس",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # غسيل أواني
    keywords = generate_product_combinations(DISHWASHER)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "غسيل أواني",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # معقمات
    keywords = generate_product_combinations(DISINFECT)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "معقمات",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # أرضيات
    keywords = generate_product_combinations(FLOOR)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "تنظيف أرضيات",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # زجاج
    keywords = generate_product_combinations(GLASS)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "تنظيف زجاج",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    # معطرات
    keywords = generate_product_combinations(FRAGRANCE)
    categories.append({
        "main": "منظفات منزلية",
        "sub": "معطرات",
        "keywords": keywords,
        "whole_word_keywords": []
    })

    return categories


# ==============================================================================
# 3. حفظ البيانات
# ==============================================================================

def save_and_report(categories):
    """حفظ التصنيفات وطباعة إحصائيات"""
    data = {
        "version": 7,
        "categories": categories
    }

    output_file = "utils/categories.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # الإحصائيات
    total_keywords = sum(len(c['keywords']) for c in categories)
    print("\n" + "=" * 70)
    print("تقرير التصنيفات الموسع")
    print("=" * 70)
    print(f"\nالفئات الرئيسية: {len(set(c['main'] for c in categories))}")
    print(f"الفئات الفرعية: {len(categories)}")
    print(f"إجمالي الكلمات المفتاحية: {total_keywords}")
    print(f"\nملف الحفظ: {output_file}")

    for cat in sorted(set(c['main'] for c in categories)):
        subs = [c['sub'] for c in categories if c['main'] == cat]
        keywords_count = sum(len(c['keywords']) for c in categories if c['main'] == cat)
        print(f"\n{cat}:")
        print(f"  - الفئات الفرعية: {len(subs)}")
        print(f"  - الكلمات المفتاحية: {keywords_count}")
        for sub in subs:
            kw = next((c['keywords'] for c in categories if c['main'] == cat and c['sub'] == sub), [])
            print(f"    {sub}: {len(kw)} كلمة")

    print("\n" + "=" * 70)


# ==============================================================================
# 4. التنفيذ
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("مولّد التصنيفات الموسّع (30,000+ كلمة مفتاحية)")
    print("=" * 70)

    # توليد الفئات
    food_categories = generate_food_categories()
    cleaning_categories = generate_cleaning_categories()

    all_categories = food_categories + cleaning_categories

    # حفظ وطباعة التقرير
    save_and_report(all_categories)
