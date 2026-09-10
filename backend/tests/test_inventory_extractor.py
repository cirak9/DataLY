import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from openpyxl import Workbook

from app.core_logic.inventory_extractor import (
    InventoryImportError,
    detect_inventory_columns,
    extract_old_inventory,
)

"""
اختبارات منطق استخراج المخزون القديم (كشف الأعمدة + تحويل الصفوف) — بمعزل تام عن
قاعدة البيانات، لأن دوال هذا الملف نصية/حسابية بحتة (ملف إكسل بالدخل، قائمة صفوف
بالخرج) بدون أي اتصال DB — نفس فلسفة core_logic/ الموثّقة بـbackend/README.md.
"""


def _xlsx_bytes(headers: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_detects_exact_arabic_column_names():
    content = _xlsx_bytes(
        ["الباركود", "اسم الصنف", "الصلاحية"],
        [["123456", "حمص فاخر", "2027-01-01"]],
    )
    rows = extract_old_inventory(io.BytesIO(content))
    assert rows == [{
        "barcode": "123456",
        "item_name": "حمص فاخر",
        "expiration_date": "2027-01-01",
        "quantity": None,
        "unit_cost": None,
    }]


def test_detects_columns_by_substring_when_exact_match_missing():
    """كود الصنف/الوصف/تاريخ الانتهاء — أسماء أعمدة مختلفة عن القائمة الدقيقة،
    لازم تنكشف بالمطابقة الجزئية (نفس فلسفة الأداة الأصلية)."""
    content = _xlsx_bytes(
        ["كود الصنف بالمحل", "وصف الصنف الكامل", "تاريخ الانتهاء المتوقع"],
        [["999", "بسكويت", "2027-06-15"]],
    )
    rows = extract_old_inventory(io.BytesIO(content))
    assert len(rows) == 1
    assert rows[0]["barcode"] == "999"
    assert rows[0]["item_name"] == "بسكويت"


def test_detects_optional_quantity_and_unit_cost_when_present():
    content = _xlsx_bytes(
        ["الباركود", "اسم الصنف", "الصلاحية", "الكمية", "سعر التكلفة"],
        [["111", "زيت زيتون", "", 25, 12.5]],
    )
    rows = extract_old_inventory(io.BytesIO(content))
    assert rows[0]["quantity"] == 25.0
    assert rows[0]["unit_cost"] == 12.5
    assert rows[0]["expiration_date"] is None  # صلاحية فاضية = None، مو تخمين


def test_missing_required_column_raises_import_error():
    content = _xlsx_bytes(["الاسم", "الصلاحية"], [["صنف بلا باركود", "2027-01-01"]])
    with pytest.raises(InventoryImportError, match="الباركود"):
        extract_old_inventory(io.BytesIO(content))


def test_rows_without_barcode_are_skipped_not_erroring():
    content = _xlsx_bytes(
        ["الباركود", "اسم الصنف", "الصلاحية"],
        [["123", "صنف سليم", ""], ["", "صنف بلا باركود يُتجاهل", ""]],
    )
    rows = extract_old_inventory(io.BytesIO(content))
    assert len(rows) == 1
    assert rows[0]["barcode"] == "123"


def test_empty_file_returns_empty_list_not_error():
    content = _xlsx_bytes(["الباركود", "اسم الصنف", "الصلاحية"], [])
    assert extract_old_inventory(io.BytesIO(content)) == []


def test_corrupt_file_raises_import_error_not_silently_empty():
    """ملف موجود بس تالف — لازم يوقف بخطأ صريح، أبداً يرجّع فاضي وكأنه أول مخزون
    (بالضبط نفس فلسفة InventoryLoadError بالأداة الأصلية: فشل حقيقي ≠ مافيش ملف)."""
    with pytest.raises(InventoryImportError):
        extract_old_inventory(io.BytesIO(b"this is not a valid xlsx file at all"))


def test_detect_inventory_columns_reports_all_missing_fields_together():
    import pandas as pd
    df = pd.DataFrame({"عمود عشوائي": ["قيمة"]})
    with pytest.raises(ValueError) as exc_info:
        detect_inventory_columns(df)
    message = str(exc_info.value)
    assert "الباركود" in message
    assert "اسم الصنف" in message
    assert "الصلاحية" in message
