import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.categorizer import get_category


def test_rice_matches():
    assert get_category("أرز أبيض ممتاز 5 كجم") == ("مواد غذائية", "أرز وحبوب")


def test_detergent_matches():
    assert get_category("مسحوق غسيل أوتوماتيك 5 كجم") == ("منظفات منزلية", "غسيل ملابس")


def test_whole_word_bayd_not_confused_with_mobayed():
    # "بيض" يجب ألا يتطابق مع "مبيض" (كلور)
    result = get_category("كلور مبيض للملابس")
    assert result != ("مواد غذائية", "ألبان ومشتقات")


def test_real_egg_matches():
    assert get_category("بيض بلدي طازج 30 حبة") == ("مواد غذائية", "ألبان ومشتقات")


def test_san_bug_fixed():
    # خلل قديم: كلمة "صن" كانت تتطابق مع أي كلمة تحتوي "صن" مثل "صنف"
    result = get_category("صنف غير معروف تماماً XYZ")
    assert result != ("منظفات منزلية", "غسيل أواني"), \
        "خلل 'صن' داخل 'صنف' لسه موجود — تأكد whole_word_keywords تحتوي 'صن'"


def test_raz_bug_cherry_not_confused_with_rice():
    # خلل مكتشف بتدقيق مركّز: "رز" (أرز) بدون whole_word كانت تتطابق داخل "كرز" (كرز)
    result = get_category("مربى كرز 500 جرام")
    assert result != ("مواد غذائية", "أرز وحبوب"), \
        "خلل 'رز' داخل 'كرز' — تأكد whole_word_keywords بـ'أرز وحبوب' تحتوي 'رز'"


def test_powder_bug_milk_powder_not_confused_with_detergent():
    # خلل مكتشف بتدقيق مركّز: كلمة "مسحوق" المجرّدة كانت تصنّف أي منتج مسحوق
    # (حليب أطفال، بروتين، بيكنج باودر) كمسحوق غسيل — أزلناها لصالح "مسحوق غسيل" الأدق
    result = get_category("مسحوق حليب أطفال 400 جرام")
    assert result != ("منظفات منزلية", "غسيل ملابس"), \
        "خلل 'مسحوق' المجرّدة يصنّف مساحيق غذائية كمنظفات — تأكد حذفها من keywords"
    assert get_category("مسحوق حليب أطفال 400 جرام") == ("مواد غذائية", "ألبان ومشتقات")


def test_mayonnaise_not_confused_with_water():
    # هشاشة كانت موجودة: "ماي" بدون whole_word تتطابق داخل "مايونيز"، وتعتمد صدفة على
    # ترتيب الفئات بملف categories.json (مياه بعد صلصات ومعلبات) — الحماية تخليها مستقلة عن الترتيب
    assert get_category("مايونيز صحي 500 مل") == ("مواد غذائية", "صلصات ومعلبات")


def test_unknown_item_falls_back():
    main, sub = get_category("جهاز كهربائي غريب تماماً")
    assert main == "مواد غذائية" and sub == "أخرى"


def test_pre_classified_sub_hint_respected():
    result = get_category("أي اسم", "فئة يدوية", "تصنيف فرعي محدد يدوياً")
    assert result == ("فئة يدوية", "تصنيف فرعي محدد يدوياً")
