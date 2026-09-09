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
    assert result != ("مواد غذائية", "منتجات ألبان")


def test_real_egg_matches():
    assert get_category("بيض بلدي طازج 30 حبة") == ("مواد غذائية", "منتجات ألبان")


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
    assert get_category("مسحوق حليب أطفال 400 جرام") == ("مواد غذائية", "منتجات ألبان")


def test_mayonnaise_not_confused_with_water():
    # هشاشة كانت موجودة: "ماي" بدون whole_word تتطابق داخل "مايونيز"، وتعتمد صدفة على
    # ترتيب الفئات بملف categories.json (مياه بعد صلصات ومعلبات) — الحماية تخليها مستقلة عن الترتيب
    assert get_category("مايونيز صحي 500 مل") == ("مواد غذائية", "صلصات ومعلبات")


def test_new_categories_from_100_item_invoice_audit():
    # 7 تصنيفات جديدة أُضيفت بعد اختبار فاتورة حقيقية بـ100 صنف طلعت "أخرى" بدونها
    assert get_category("شعيرية رفيعة 400 جرام") == ("مواد غذائية", "أرز وحبوب")
    assert get_category("برغل ناعم 1 كجم") == ("مواد غذائية", "أرز وحبوب")
    assert get_category("بيكنج باودر مسحوق خبيز 100 جرام") == ("مواد غذائية", "معجنات ودقيق")
    assert get_category("مربى كرز 400 جرام") == ("مواد غذائية", "مربيات وعسل")
    assert get_category("عسل نحل طبيعي 500 جرام") == ("مواد غذائية", "مربيات وعسل")
    assert get_category("زيتون أسود معلب 400 جرام") == ("مواد غذائية", "زيتون ومخللات")
    assert get_category("مسحوق بروتين رياضي 500 جرام") == ("مواد غذائية", "مكملات غذائية")


def test_whole_word_asal_not_confused_with_moassal():
    # "عسل" يجب ألا يتطابق مع "معسل" (تبغ الشيشة) — خطر مشابه لخلل "صن"/"صنف"
    result = get_category("معسل تفاح 250 جرام")
    assert result != ("مواد غذائية", "مربيات وعسل")


def test_unknown_item_falls_back():
    main, sub = get_category("جهاز كهربائي غريب تماماً")
    assert main == "مواد غذائية" and sub == "أخرى"


def test_pre_classified_sub_hint_respected():
    result = get_category("أي اسم", "فئة يدوية", "تصنيف فرعي محدد يدوياً")
    assert result == ("فئة يدوية", "تصنيف فرعي محدد يدوياً")
