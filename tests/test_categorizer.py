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


def test_unknown_item_falls_back():
    main, sub = get_category("جهاز كهربائي غريب تماماً")
    assert main == "مواد غذائية" and sub == "أخرى"


def test_pre_classified_sub_hint_respected():
    result = get_category("أي اسم", "فئة يدوية", "تصنيف فرعي محدد يدوياً")
    assert result == ("فئة يدوية", "تصنيف فرعي محدد يدوياً")
