import sys, os
import pandas as pd
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fusion.reconciliation import (
    reconcile_dataframes, load_master, resolve_conflicts_interactively,
    MasterDataError, MASTER_COLUMNS,
)


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


def test_barcode_match_with_different_size_is_flagged_not_replaced():
    # نفس الحالة الحقيقية اللي اكتُشفت: "سكر ناعم 10 كجم" مقابل "سكر التميز 1 كغ" —
    # تشابه نصي عالي (كلمة "سكر" مشتركة) لكن الحجم مختلف 10 أضعاف فعليًا.
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 200, "الصندوق": 1, "تكلفة الوحدة": 27.44, "الإجمالي": 5488.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "6289000001660"}])
    master = _master([{
        "الباركود": "6289000001660", "اسم الصنف": "سكر التميز 1 كغ",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "سكر",
    }])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"  # لا استبدال أعمى
    assert len(warnings) == 1
    assert "حجم" in warnings[0]["السبب"]


def test_barcode_match_with_same_size_different_wording_still_replaces():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "معكرونة اسباجيتي 500 غ", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 80, "الصندوق": 1, "تكلفة الوحدة": 23.275, "الإجمالي": 1862.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "111222"}])
    master = _master([{
        "الباركود": "111222", "اسم الصنف": "معكرونة إسباجيتي 500 جرام",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "معكرونة ومعجنات",
    }])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "معكرونة إسباجيتي 500 جرام"
    assert warnings == []


def test_missing_barcode_fuzzy_match_skipped_when_size_differs():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 200, "الصندوق": 1, "تكلفة الوحدة": 27.44, "الإجمالي": 5488.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": ""}])
    master = _master([{
        "الباركود": "6289000001660", "اسم الصنف": "سكر التميز 1 كغ",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "سكر",
    }])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"  # ما تطابق رغم تشابه الاسم
    assert warnings == []  # فشل fuzzy fallback بدون باركود لا يستحق تحذير (طبيعي)


def test_barcode_match_with_different_unit_category_is_flagged():
    # نفس الحالة الحقيقية الثانية: "5 كجم" (وزن) مقابل "250 مل" (حجم) — نوع قياس مختلف
    # كليًا، ما نقدر نقارن الأرقام رياضيًا، لكن الاختلاف بحد ذاته مؤشر شك.
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "مسحوق غسيل أوتوماتيك 5 كجم", "التصنيف الرئيسي": "منظفات منزلية",
        "التصنيف الفرعي": "أخرى", "العدد": 90, "الصندوق": 1, "تكلفة الوحدة": 41.4, "الإجمالي": 3726.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "6289000000422"}])
    master = _master([{
        "الباركود": "6289000000422", "اسم الصنف": "مساحيق غسيل التميز 250 مل",
        "التصنيف الرئيسي": "منظفات", "التصنيف الفرعي": "مساحيق غسيل",
    }])

    out_inv, _, _, warnings = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "مسحوق غسيل أوتوماتيك 5 كجم"
    assert len(warnings) == 1
    assert "قياس" in warnings[0]["السبب"]


def test_resolve_conflicts_default_keeps_original_name(monkeypatch):
    df_inv = _inv([{"item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم"}])
    master = _master([{"الباركود": "123", "اسم الصنف": "سكر التميز 1 كغ"}])
    review_rows = [{
        "item_id": 1, "الباركود": "123", "الاسم بالفاتورة": "سكر ناعم 10 كجم",
        "الاسم المعتمد بقاعدة الأصناف": "سكر التميز 1 كغ", "نسبة التشابه": 67,
        "السبب": "اختلاف حجم",
    }]

    monkeypatch.setattr("builtins.input", lambda *_: "1")
    out_inv, out_master = resolve_conflicts_interactively(df_inv, master, review_rows)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"
    assert out_master.iloc[0]["اسم الصنف"] == "سكر التميز 1 كغ"  # master لم يتغيّر
    assert review_rows[0]["القرار"] == "إكمال بالاسم الأصلي بالفاتورة"


def test_resolve_conflicts_manual_naming_updates_invoice_and_master(monkeypatch):
    df_inv = _inv([{"item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم"}])
    master = _master([{"الباركود": "123", "اسم الصنف": "سكر التميز 1 كغ"}])
    review_rows = [{
        "item_id": 1, "الباركود": "123", "الاسم بالفاتورة": "سكر ناعم 10 كجم",
        "الاسم المعتمد بقاعدة الأصناف": "سكر التميز 1 كغ", "نسبة التشابه": 67,
        "السبب": "اختلاف حجم",
    }]

    responses = iter(["2", "سكر ناعم 10 كجم (تأكيد يدوي)"])
    monkeypatch.setattr("builtins.input", lambda *_: next(responses))
    out_inv, out_master = resolve_conflicts_interactively(df_inv, master, review_rows)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم (تأكيد يدوي)"
    assert out_master.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم (تأكيد يدوي)"
    assert review_rows[0]["القرار"] == "تسمية يدوية: سكر ناعم 10 كجم (تأكيد يدوي)"


def test_resolve_conflicts_non_interactive_run_defaults_gracefully(monkeypatch):
    df_inv = _inv([{"item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم"}])
    master = _master([{"الباركود": "123", "اسم الصنف": "سكر التميز 1 كغ"}])
    review_rows = [{
        "item_id": 1, "الباركود": "123", "الاسم بالفاتورة": "سكر ناعم 10 كجم",
        "الاسم المعتمد بقاعدة الأصناف": "سكر التميز 1 كغ", "نسبة التشابه": 67,
        "السبب": "اختلاف حجم",
    }]

    def _raise_eof(*_):
        raise EOFError
    monkeypatch.setattr("builtins.input", _raise_eof)

    out_inv, out_master = resolve_conflicts_interactively(df_inv, master, review_rows)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"
    assert review_rows[0]["القرار"] == "إكمال بالاسم الأصلي بالفاتورة"


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


def test_load_master_missing_barcode_column_raises_clear_error(tmp_path):
    df = pd.DataFrame({"اسم الصنف": ["أرز أبيض ممتاز 5 كجم"]})
    path = tmp_path / "master_no_barcode.xlsx"
    df.to_excel(path, index=False)

    with pytest.raises(MasterDataError):
        load_master(str(path))


def test_load_master_recognizes_broad_synonym_headers(tmp_path):
    # أسماء أعمدة بعيدة عن التسمية الافتراضية، للتأكد إن الموسوعة الواسعة تغطيها
    df = pd.DataFrame({
        "رمز المنتج": ["999111"],
        "وصف المنتج": ["سكر ناعم 10 كجم"],
    })
    path = tmp_path / "master_synonyms.xlsx"
    df.to_excel(path, index=False)

    result = load_master(str(path))

    assert result.iloc[0]["الباركود"] == "999111"
    assert result.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"


def test_load_master_missing_file_returns_empty_frame(tmp_path):
    result = load_master(str(tmp_path / "no_such_file.xlsx"))
    assert list(result.columns) == MASTER_COLUMNS
    assert result.empty
