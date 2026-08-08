import sys, os
import pandas as pd
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fusion.reconciliation import (
    reconcile_dataframes, resolve_matches_interactively, load_master,
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


# ── reconcile_dataframes(): تحضير التطابقات المُقترَحة (بدون تطبيق أي استبدال) ──────

def test_new_barcode_registers_automatically_without_pending_match():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "صنف جديد كليًا", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 5, "الصندوق": 1, "تكلفة الوحدة": 2.0, "الإجمالي": 10.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "999000"}])
    master = _master([])

    out_inv, out_ses, out_master, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert pending == []  # صنف جديد لا يحتاج موافقة
    assert out_inv.iloc[0]["اسم الصنف"] == "صنف جديد كليًا"
    assert "999000" in out_master["الباركود"].tolist()
    assert out_master[out_master["الباركود"] == "999000"].iloc[0]["اسم الصنف"] == "صنف جديد كليًا"


def test_known_barcode_creates_pending_match_without_auto_replace():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "123456"}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    # ما فيه استبدال تلقائي — الاسم بالفاتورة يبقى كما هو لحد الموافقة
    assert out_inv.iloc[0]["اسم الصنف"] == "رز ابيض فاخر 5ك"
    assert len(pending) == 1
    assert pending[0]["الاسم المقترح"] == "أرز أبيض ممتاز 5 كجم"
    assert pending[0]["طريقة المطابقة"] == "باركود"
    assert pending[0]["تنبيه"] == ""  # تشابه مقبول، بدون تنبيه


def test_pending_match_flags_low_name_similarity():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "منظف أرضيات لافندر", "التصنيف الرئيسي": "منظفات منزلية",
        "التصنيف الفرعي": "أخرى", "العدد": 3, "الصندوق": 1, "تكلفة الوحدة": 4.0, "الإجمالي": 12.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "555111"}])
    master = _master([{
        "الباركود": "555111", "اسم الصنف": "شامبو أطفال 200 مل",
        "التصنيف الرئيسي": "عناية شخصية", "التصنيف الفرعي": "أخرى",
    }])

    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert len(pending) == 1
    assert pending[0]["تنبيه"] != ""


def test_pending_match_flags_size_mismatch_same_unit_category():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 200, "الصندوق": 1, "تكلفة الوحدة": 27.44, "الإجمالي": 5488.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "6289000001660"}])
    master = _master([{
        "الباركود": "6289000001660", "اسم الصنف": "سكر التميز 1 كغ",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "سكر",
    }])

    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert len(pending) == 1
    assert "حجم" in pending[0]["تنبيه"]


def test_pending_match_flags_different_unit_category():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "مسحوق غسيل أوتوماتيك 5 كجم", "التصنيف الرئيسي": "منظفات منزلية",
        "التصنيف الفرعي": "أخرى", "العدد": 90, "الصندوق": 1, "تكلفة الوحدة": 41.4, "الإجمالي": 3726.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "6289000000422"}])
    master = _master([{
        "الباركود": "6289000000422", "اسم الصنف": "مساحيق غسيل التميز 250 مل",
        "التصنيف الرئيسي": "منظفات", "التصنيف الفرعي": "مساحيق غسيل",
    }])

    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert len(pending) == 1
    assert "قياس" in pending[0]["تنبيه"]


def test_missing_barcode_creates_pending_fuzzy_match_above_threshold():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": ""}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "رز ابيض فاخر 5ك"  # بدون استبدال تلقائي
    assert len(pending) == 1
    assert pending[0]["طريقة المطابقة"] == "اسم تقريبي (بدون باركود)"
    assert pending[0]["الاسم المقترح"] == "أرز أبيض ممتاز 5 كجم"


def test_missing_barcode_no_match_below_threshold_creates_no_pending_match():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "صنف غريب تمامًا XYZ", "التصنيف الرئيسي": "مواد غذائية",
        "التصنيف الفرعي": "أخرى", "العدد": 1, "الصندوق": 1, "تكلفة الوحدة": 1.0, "الإجمالي": 1.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": ""}])
    master = _master([{
        "الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
    }])

    out_inv, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    assert out_inv.iloc[0]["اسم الصنف"] == "صنف غريب تمامًا XYZ"
    assert pending == []


# ── resolve_matches_interactively(): القرار البشري الفعلي ──────────────────────────

def test_approving_match_applies_name_and_category_and_marks_canonical():
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
    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    out_inv, out_ses, out_master, decisions = resolve_matches_interactively(
        df_inv, df_ses, master, pending, choices=iter(["1"])
    )

    assert out_inv.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert out_inv.iloc[0]["التصنيف الفرعي"] == "أرز وحبوب"
    assert decisions[0]["القرار"] == "موافقة — اعتُمد الاسم المقترح"


def test_rejecting_match_keeps_original_name():
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
    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    out_inv, _, out_master, decisions = resolve_matches_interactively(
        df_inv, df_ses, master, pending, choices=iter(["2"])
    )

    assert out_inv.iloc[0]["اسم الصنف"] == "رز ابيض فاخر 5ك"
    assert out_master.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"  # master لم يتغيّر
    assert decisions[0]["القرار"] == "رفض — إبقاء الاسم الأصلي"


def test_manual_naming_updates_invoice_and_master():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أخرى",
        "العدد": 200, "الصندوق": 1, "تكلفة الوحدة": 27.44, "الإجمالي": 5488.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "6289000001660"}])
    master = _master([{
        "الباركود": "6289000001660", "اسم الصنف": "سكر التميز 1 كغ",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "سكر",
    }])
    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    out_inv, _, out_master, decisions = resolve_matches_interactively(
        df_inv, df_ses, master, pending, choices=iter(["3", "سكر ناعم 10 كجم (مؤكَّد)"])
    )

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم (مؤكَّد)"
    assert out_master.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم (مؤكَّد)"
    assert decisions[0]["القرار"] == "تسمية يدوية: سكر ناعم 10 كجم (مؤكَّد)"


def test_non_interactive_run_defaults_to_rejection_without_hanging(monkeypatch):
    df_inv = _inv([{"item_id": 1, "اسم الصنف": "سكر ناعم 10 كجم"}])
    df_ses = _ses([{"item_id": 1, "الباركود": "123"}])
    master = _master([{"الباركود": "123", "اسم الصنف": "سكر التميز 1 كغ"}])
    pending = [{
        "item_id": 1, "الباركود": "123", "طريقة المطابقة": "باركود",
        "الاسم بالفاتورة": "سكر ناعم 10 كجم", "الاسم المقترح": "سكر التميز 1 كغ",
        "التصنيف الرئيسي المقترح": "", "التصنيف الفرعي المقترح": "",
        "نسبة التشابه": 67, "تنبيه": "اختلاف حجم",
    }]

    def _raise_eof(*_):
        raise EOFError
    monkeypatch.setattr("builtins.input", _raise_eof)

    out_inv, _, _, decisions = resolve_matches_interactively(df_inv, df_ses, master, pending)

    assert out_inv.iloc[0]["اسم الصنف"] == "سكر ناعم 10 كجم"
    assert decisions[0]["القرار"] == "رفض — إبقاء الاسم الأصلي"


def test_two_approved_matches_same_barcode_are_merged():
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
    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)
    assert len(pending) == 2

    out_inv, out_ses, _, decisions = resolve_matches_interactively(
        df_inv, df_ses, master, pending, choices=iter(["1", "1"])
    )

    assert len(out_inv) == 1
    row = out_inv.iloc[0]
    assert row["item_id"] == 1
    assert row["العدد"] == 14
    assert row["الإجمالي"] == 70.0
    assert row["تكلفة الوحدة"] == round(70.0 / 14, 3)
    assert len(out_ses) == 1


def test_master_without_category_columns_keeps_existing_category_on_approval():
    df_inv = _inv([{
        "item_id": 1, "اسم الصنف": "رز ابيض فاخر 5ك",
        "التصنيف الرئيسي": "مواد غذائية", "التصنيف الفرعي": "أرز وحبوب",
        "العدد": 10, "الصندوق": 1, "تكلفة الوحدة": 5.0, "الإجمالي": 50.0,
    }])
    df_ses = _ses([{"item_id": 1, "الباركود": "123456"}])
    # master بدون بيانات تصنيف معتمدة (بيانات مستلمة ناقصة التفصيل)
    master = _master([{"الباركود": "123456", "اسم الصنف": "أرز أبيض ممتاز 5 كجم"}])
    _, _, _, pending = reconcile_dataframes(df_inv, df_ses, master)

    out_inv, _, _, _ = resolve_matches_interactively(
        df_inv, df_ses, master, pending, choices=iter(["1"])
    )

    assert out_inv.iloc[0]["اسم الصنف"] == "أرز أبيض ممتاز 5 كجم"
    assert out_inv.iloc[0]["التصنيف الفرعي"] == "أرز وحبوب"  # بقي كما صنّفه categorizer.py سابقًا


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
