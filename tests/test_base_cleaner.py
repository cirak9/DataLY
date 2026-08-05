import sys, os
import pandas as pd
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from transformers.base_cleaner import clean_data
from utils.validators import InvoiceValidationError


def test_removes_zero_qty_and_price_rows():
    df = pd.DataFrame({
        "اسم الصنف": ["صنف حقيقي", "صنف فاضي"],
        "الكمية": [10, 0],
        "سعر الشراء": [5, 0],
    })
    result = clean_data(df)
    assert len(result) == 1
    assert result.iloc[0]["item_name"] == "صنف حقيقي"


def test_removes_note_rows():
    df = pd.DataFrame({
        "اسم الصنف": ["أرز", "ملاحظة: البضاعة المباعة لا تُرد"],
        "الكمية": [10, 0],
        "سعر الشراء": [5, 0],
    })
    result = clean_data(df)
    assert len(result) == 1


def test_missing_item_name_column_raises_clear_error():
    df = pd.DataFrame({"الكمية": [1, 2], "سعر الشراء": [5, 6]})
    with pytest.raises(InvoiceValidationError):
        clean_data(df)


def test_empty_after_cleaning_raises_error():
    df = pd.DataFrame({
        "اسم الصنف": ["ملاحظة فقط"],
        "الكمية": [0],
        "سعر الشراء": [0],
    })
    with pytest.raises(InvoiceValidationError):
        clean_data(df)
