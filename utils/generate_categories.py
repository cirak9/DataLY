# utils/generate_categories.py — مولّد تصنيفات شامل
# يولّد آلاف التصنيفات للمنتجات الغذائية ومواد التنظيف

import json
from itertools import product

# ==============================================================================
# 1. قائمة شاملة من المنتجات الغذائية (عربي + إنجليزي)
# ==============================================================================

GRAINS_CEREALS = {
    "ar": ["أرز", "رز", "قمح", "شعير", "ذرة", "شوفان", "جاودار", "بسمتي", "بوند", "كسكس", "برغل"],
    "en": ["rice", "wheat", "barley", "corn", "oats", "rye", "basmati", "pound", "couscous", "bulgur"]
}

FLOUR_BAKING = {
    "ar": ["دقيق", "طحين", "نشا", "جلوتين", "خميرة", "بيكنج بودر", "صودا الخبز", "ملح الطعام"],
    "en": ["flour", "meal", "starch", "gluten", "yeast", "baking powder", "baking soda", "table salt"]
}

PASTA_NOODLES = {
    "ar": ["معكرونة", "سباغيتي", "إسباجيتي", "نودلز", "باستا", "فتوتشيني", "بينيه", "ريجاتوني"],
    "en": ["pasta", "spaghetti", "noodles", "fettuccini", "penne", "rigatoni", "lasagna", "macaroni"]
}

SUGAR_SWEETS = {
    "ar": ["سكر", "عسل", "مربى", "شيكولاتة", "حلوى", "شكولاتة", "مارملاد", "كراميل"],
    "en": ["sugar", "honey", "jam", "chocolate", "candy", "marmalade", "caramel", "syrup"]
}

OILS_FATS = {
    "ar": ["زيت", "زيت زيتون", "زيت نخيل", "زيت جوز هند", "سمن", "زبدة", "قشطة"],
    "en": ["oil", "olive oil", "palm oil", "coconut oil", "ghee", "butter", "cream"]
}

SPICES_SEASONINGS = {
    "ar": ["ملح", "فلفل", "كمون", "قرفة", "زعتر", "بهارات", "كزبرة", "ينسون", "شطة", "فلفل حار", "هيل"],
    "en": ["salt", "pepper", "cumin", "cinnamon", "thyme", "spice", "coriander", "anise", "chili", "cardamom"]
}

SAUCES_CONDIMENTS = {
    "ar": ["صلصة", "معجون", "كاتشب", "مايونيز", "خردل", "صوص", "طحينة", "صلصة سويا"],
    "en": ["sauce", "paste", "ketchup", "mayonnaise", "mustard", "tahini", "soy sauce", "vinegar"]
}

CANNED_PRESERVED = {
    "ar": ["معلب", "معلبات", "تونة", "سردين", "فول", "حمص", "عدس", "ذرة", "بازلاء", "طماطم"],
    "en": ["canned", "tinned", "tuna", "sardines", "beans", "chickpeas", "lentils", "corn", "peas", "tomato"]
}

DAIRY_EGGS = {
    "ar": ["حليب", "لبن", "لبنة", "جبن", "زبادي", "يوغرت", "جبنة بيضاء", "كريمة", "بيض"],
    "en": ["milk", "yogurt", "cheese", "cream", "butter", "cottage cheese", "egg", "eggs", "curd"]
}

BEVERAGES = {
    "ar": ["قهوة", "شاي", "عصير", "نسكافيه", "كاكاو", "قهوة منزوعة الكافيين", "شاي أخضر", "مشروب"],
    "en": ["coffee", "tea", "juice", "cocoa", "beverage", "soft drink", "water", "mineral water", "energy drink"]
}

NUTS_DRIED_FRUITS = {
    "ar": ["لوز", "فستق", "جوز", "كاجو", "فول سوداني", "زبيب", "تمر", "جوز الهند", "بندق"],
    "en": ["almond", "pistachio", "walnut", "cashew", "peanut", "raisin", "date", "coconut", "hazelnut"]
}

BABY_FOOD = {
    "ar": ["حليب أطفال", "غذاء الأطفال", "حليب بودرة", "عصيدة", "فطام", "بسكويت أطفال"],
    "en": ["baby milk", "baby food", "infant formula", "powdered milk", "cereal", "baby biscuit"]
}

# ==============================================================================
# 2. قائمة شاملة من مواد التنظيف
# ==============================================================================

LAUNDRY_CLEANING = {
    "ar": ["مسحوق غسيل", "سائل غسيل", "منظف الملابس", "مبيض الملابس", "ملعّن", "مطري النسيج"],
    "en": ["laundry powder", "laundry liquid", "detergent", "bleach", "fabric softener", "starch"]
}

DISHWASHING = {
    "ar": ["سائل جلي", "منظف الأطباق", "فيري", "صن", "جل الأطباق", "منظف القدور"],
    "en": ["dishwashing liquid", "dish soap", "dish gel", "plate cleaner", "grease remover"]
}

DISINFECTANTS = {
    "ar": ["كلور", "مبيض", "معقّم", "ديتول", "دومستوس", "لايزول", "معقّم يدين", "مضاد جراثيم"],
    "en": ["chlorine", "bleach", "disinfectant", "antibacterial", "sanitizer", "germicide", "sterilizer"]
}

FLOOR_CLEANERS = {
    "ar": ["منظف أرضيات", "معقّم أرضيات", "سائل أرضيات", "واكس", "لمّاع الأرضيات"],
    "en": ["floor cleaner", "floor disinfectant", "floor liquid", "wax", "floor polish", "tile cleaner"]
}

WINDOW_GLASS = {
    "ar": ["منظف زجاج", "منظف النوافذ", "سائل زجاج", "مرآة"],
    "en": ["glass cleaner", "window cleaner", "glass liquid", "mirror cleaner"]
}

AIR_FRESHENERS = {
    "ar": ["معطّر جو", "بخاخ جو", "أير فريش", "معطّر رائحة", "شمعة معطّرة"],
    "en": ["air freshener", "room spray", "odor eliminator", "scent spray", "fragrance"]
}

CLEANING_TOOLS = {
    "ar": ["إسفنجة", "ليفة", "سكوتش", "فرشاة", "مكنسة", "مجرفة", "قفازات", "فراشي"],
    "en": ["sponge", "scrubber", "brush", "broom", "dustpan", "gloves", "mop", "cloth"]
}

SPECIALTY_CLEANERS = {
    "ar": ["منظف المعادن", "منظف الفولاذ", "منظف الخشب", "منظف الرخام", "منظف السيراميك", "مزيل الجير"],
    "en": ["metal cleaner", "steel cleaner", "wood cleaner", "marble cleaner", "tile cleaner", "limescale remover"]
}

# ==============================================================================
# 3. بنية التصنيفات
# ==============================================================================

CATEGORY_STRUCTURE = {
    "مواد غذائية": {
        "أرز وحبوب": GRAINS_CEREALS,
        "معجنات ودقيق": FLOUR_BAKING,
        "معكرونة ومعجنات": PASTA_NOODLES,
        "السكريات والحلويات": SUGAR_SWEETS,
        "زيوت ودهون": OILS_FATS,
        "توابل وبهارات": SPICES_SEASONINGS,
        "صلصات وتتبيلات": SAUCES_CONDIMENTS,
        "معلبات ومحفوظات": CANNED_PRESERVED,
        "منتجات ألبان": DAIRY_EGGS,
        "المشروبات": BEVERAGES,
        "مكسرات وفواكه مجففة": NUTS_DRIED_FRUITS,
        "غذاء الأطفال": BABY_FOOD,
    },
    "منظفات منزلية": {
        "غسيل ملابس": LAUNDRY_CLEANING,
        "غسيل أواني": DISHWASHING,
        "معقمات": DISINFECTANTS,
        "تنظيف أرضيات": FLOOR_CLEANERS,
        "تنظيف زجاج": WINDOW_GLASS,
        "معطرات": AIR_FRESHENERS,
        "أدوات تنظيف": CLEANING_TOOLS,
        "منظفات متخصصة": SPECIALTY_CLEANERS,
    }
}

# ==============================================================================
# 4. دوال التوليد
# ==============================================================================

def generate_keywords_combinations():
    """توليد جميع التصنيفات والكلمات المفتاحية"""
    categories = []

    for main_cat, subcategories in CATEGORY_STRUCTURE.items():
        for sub_cat, word_dict in subcategories.items():
            ar_words = word_dict.get("ar", [])
            en_words = word_dict.get("en", [])

            # دمج العربية والإنجليزية
            all_keywords = ar_words + en_words

            # تحديد الكلمات التي تحتاج whole_word_keywords
            # (الكلمات التي قد تتطابق مع كلمات أخرى)
            whole_words = []

            # كلمات قصيرة وغير آمنة
            unsafe_patterns = ["صن", "رز", "ملح", "ماي", "عسل", "لبن", "بيض", "سمن", "خل", "زيت", "برغل"]
            for word in all_keywords:
                if any(unsafe in word for unsafe in unsafe_patterns) and len(word) <= 4:
                    whole_words.append(word)

            categories.append({
                "main": main_cat,
                "sub": sub_cat,
                "keywords": all_keywords,
                "whole_word_keywords": whole_words
            })

    return categories


def save_categories_json(categories: list, output_file: str = "utils/categories.json"):
    """حفظ التصنيفات في ملف JSON"""
    data = {
        "version": 7,
        "categories": categories
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] تم حفظ {len(categories)} فئة في {output_file}")
    print(f"  - إجمالي الكلمات المفتاحية: {sum(len(c['keywords']) for c in categories)}")


# ==============================================================================
# 5. التنفيذ
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("مولّد التصنيفات الشامل")
    print("=" * 70)

    categories = generate_keywords_combinations()

    print(f"\nالتصنيفات المولّدة:")
    for main_cat, subcategories in CATEGORY_STRUCTURE.items():
        print(f"\n{main_cat}:")
        for sub_cat in subcategories.keys():
            print(f"  - {sub_cat}")

    print(f"\nإجمالي التصنيفات: {len(categories)}")

    # حفظ
    save_categories_json(categories)

    print("\n" + "=" * 70)
    print("اكتمل توليد التصنيفات!")
    print("=" * 70)
