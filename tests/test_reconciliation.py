import sys, os
import pandas as pd
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fusion.reconciliation import reconcile_dataframes, load_master, MasterDataError, MASTER_COLUMNS


def _inv(rows):
    return pd.DataFrame(rows)


def _ses(rows):
    return pd.DataFrame(rows)


def _master(rows):
    df = pd.DataFrame(rows)
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[MASTER_COLUMNS]


def test_known_barcode_replaces_name_and_category():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أخرى",
        "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "123456"}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, out_ses, out_master, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert out_inv.iloc[0]["التصنيف الفرعي"] == "أرز وحبوب"
    assert warnings == []


def test_new_barcode_registers_without_warning():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "صنف جديد كليًا", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 5, "الصندوق": 1, "تكلفة الوحدة": 2.0, "الإجمالي": 10.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "999000"}])
    master = _master([])

    out_inv, out_ses, out_master, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "صنف جديد كليًا"  # الاسم الأصلي يبقى كما هو
    assert warnings == []  # صنف جديد لا يستحق تحذير
    assert "999000" in out_master["الباركود"].tolist()
    assert out_master[out_master["الباركود"] == "999000"].iloc[0]["اسم الصنف"] == "صنف جديد كليًا"


def test_conflicting_name_for_known_barcode_raises_warning_not_overwrite():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "منظف أرضيات لافندر", "التصنيف الرئيسي": "منظفات منزلية",
        "التصنيف الفرعي": "أخرى", "العدد": 3, "الصندوق": 1, "تكلفة الوحدة": 4.0, "الإجمالي": 12.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "555111"}])
    master = _master([{
        "الباركود": "555111", "اسم الصنف": "شامبو أطفال 200 مل",
        "التصنيف الرئيسي": "عناية شخصية", "التصنيف الفرعي": "أخرى",
    }])

    out_inv, out_ses, out_master, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "منظف أرضيات لافندر"  # لا استبدال أعمى
    assert len(warnings) == 1
    assert warnings[0]["الباركود"] == "555111"


def test_missing_barcode_falls_back_to_fuzzy_name_match():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": ""}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, out_ses, out_master, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert warnings == []


def test_missing_barcode_no_match_stays_unchanged():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "صنف غريب تمامًا XYZ", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 1, "الصندوق": 1, "تكلفة الوحدة": 1.0, "الإجمالي": 1.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": ""}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "صنف غريب تمامًا XYZ"
    assert warnings == []


def test_master_without_category_columns_keeps_existing_category():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أرز وحبوب", "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "123456"}])
    # master بدون بيانات تصنيف معتمدة (بيانات مستلمة ناقصة التفصيل)
    master = _master([{"الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم"}])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert out_inv.iloc[0]["التصنيف الفرعي"] == "أرز وحبوب"  # بقي كما صنّفه categorizer.py سابقًا
    assert warnings == []


def test_duplicate_items_same_barcode_are_merged_and_totals_summed():
    df_inv = _inv([
        {"item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك", "التصنيف الرئيسي": "مواد غذائية",
         "التصنيف الفرعي": "أخرى", "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0},
        {"item_id": 2, "اسم الصنف": "أرز ابيض ممتاز 5كجم", "التصنيف الرئيسي": "مواد غذائية",
         "التصنيف الفرعي": "أخرى", "العدد": 4, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 20.0},
    ])
    df_ses = _ses([
        {"item_id": 1, "الباركود": "123456"},
        {"item_id": 2, "الباركود": "123456"},
    ])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, out_ses, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert len(out_inv) == 1
    row = out_inv.iloc[0]
    assert row["item_id"] == 1
    assert row["العدد"] == 14
    assert row["الإجمالي"] == 70.0
    assert row["تكلفة الوحدة"] == round(70.0 / 14, 3)
    assert len(out_ses) == 1
    assert warnings == []


def test_load_master_detects_alsahl_style_headers(tmp_path):
    # نفس تسمية أعمدة منظومة السهل الحقيقية بملف "فاتورة مشتريات": الكود = باركود، الوصف = الاسم
    df = pd.DataFrame({
        "الكود": ["47960025", "12345678"],
        "الوصف": ["شاي الزهرة الذهبية", "أرز أبيض ممتاز 5 كجم"],
        "رئيسي": ["مواد غذائية", "مواد غذائية"],
        "فرعي": ["شاي وقهوة", "أرز وحبوب"],
    })
    path = tmp_path / "master_alsahl.xlsx"
    df.to_excel(path, index=False)

    result = load_master(str(path))

    assert list(result.columns) == MASTER_COLUMNS
    assert result.iloc[0]["الباركود"] == "47960025"
    assert result.iloc[0]["اسم الصنف"] == "شاي الزهرة الذهبية"
    assert result.iloc[0]["التصنيف الرئيسي"] == "مواد غذائية"
    assert result.iloc[1]["التصنيف الفرعي"] == "أرز وحبوب"


def test_load_master_missing_name_column_raises_clear_error(tmp_path):
    df = pd.DataFrame({"الكود": ["123"], "السعر": [5.0]})
    path = tmp_path / "master_broken.xlsx"
    df.to_excel(path, index=False)

    with pytest.raises(MasterDataError):
        load_master(str(path))


def test_load_master_missing_barcode_column_still_loads_with_warning(tmp_path):
    df = pd.DataFrame({"اسم الصنف": ["أرز أبيض ممتاز 5 كجم"]})
    path = tmp_path / "master_no_barcode.xlsx"
    df.to_excel(path, index=False)

    result = load_master(str(path))

    assert list(result.columns) == MASTER_COLUMNS
    assert result.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert result.iloc[0]["الباركود"] == ""


def test_load_master_missing_file_returns_empty_frame(tmp_path):
    result = load_master(str(tmp_path / "no_such_file.xlsx"))
    assert list(result.columns) == MASTER_COLUMNS
    assert result.empty
