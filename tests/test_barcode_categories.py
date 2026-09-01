import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import pytest
from utils import barcode_categories as bc


@pytest.fixture(autouse=True)
def isolated_index(tmp_path, monkeypatch):
    """كل اختبار يشتغل على ملف فهرس مؤقت منفصل، بلا أي أثر على data/barcode_categories.json الحقيقي."""
    monkeypatch.setattr(bc, "_INDEX_PATH", str(tmp_path / "barcode_categories.json"))
    bc._cache = None
    yield
    bc._cache = None


def test_lookup_unknown_barcode_returns_none():
    assert bc.lookup("0000000000000") is None


def test_learn_then_lookup():
    assert bc.learn("6221031000015", "مواد غذائية", "أرز وحبوب", "أرز أبيض ممتاز 5 كجم", "store_1")
    assert bc.lookup("6221031000015") == ("مواد غذائية", "أرز وحبوب")


def test_learn_rejects_empty_or_generic_category():
    assert bc.learn("123", "مواد غذائية", "أخرى") is False
    assert bc.learn("", "مواد غذائية", "أرز وحبوب") is False
    assert bc.lookup("123") is None


def test_learn_persists_across_reload():
    bc.learn("999", "منظفات منزلية", "غسيل ملابس")
    bc._cache = None  # يحاكي إعادة تشغيل البرنامج (قراءة من القرص من جديد)
    assert bc.lookup("999") == ("منظفات منزلية", "غسيل ملابس")


def test_most_recent_learn_wins_on_conflict():
    bc.learn("555", "مواد غذائية", "أرز وحبوب", store_id="store_1")
    bc.learn("555", "مواد غذائية", "سكر وملح", store_id="store_2")
    assert bc.lookup("555") == ("مواد غذائية", "سكر وملح")


def test_learn_from_dataframe_skips_rows_without_real_category():
    df = pd.DataFrame([
        {"الباركود": "111", "اسم الصنف": "صنف مصنّف", "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب"},
        {"الباركود": "222", "اسم الصنف": "صنف بلا تصنيف", "التصنيف الرئيسي": "", "التصنيف الفرعي": ""},
    ])
    learned = bc.learn_from_dataframe(df, "الباركود", "التصنيف الرئيسي", "التصنيف الفرعي", "اسم الصنف", "store_1")
    assert learned == 1
    assert bc.lookup("111") == ("مواد غذائية", "أرز وحبوب")
    assert bc.lookup("222") is None


def test_categorizer_prefers_barcode_index_over_keywords():
    from utils.categorizer import get_category
    get_category.cache_clear()
    try:
        bc.learn("6221099999999", "عناية شخصية", "عناية بالفم", "أرز مموّه (اختبار)")
        # الاسم يحتوي كلمة "أرز" (تُصنَّف عادة أرز وحبوب) لكن الباركود بالفهرس يتغلّب
        assert get_category("أرز مموّه", "", "", "6221099999999") == ("عناية شخصية", "عناية بالفم")
    finally:
        get_category.cache_clear()
