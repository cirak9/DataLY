import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.core_logic.ocr_extractor import OcrParseError, parse_extraction_response


def test_parses_valid_json_array():
    text = """[
        {"source_image": 1, "item_name": "زيت ذرة", "quantity": 12, "unit_cost": 8.75, "barcode": "123", "confidence": "high"}
    ]"""
    items = parse_extraction_response(text)
    assert len(items) == 1
    assert items[0]["item_name"] == "زيت ذرة"
    assert items[0]["quantity"] == 12
    assert items[0]["barcode"] == "123"
    assert items[0]["confidence"] == "high"


def test_strips_surrounding_markdown_fence():
    text = '```json\n[{"source_image": 1, "item_name": "سكر", "quantity": 5, "unit_cost": 3}]\n```'
    items = parse_extraction_response(text)
    assert items[0]["item_name"] == "سكر"


def test_defaults_missing_confidence_to_medium():
    text = '[{"source_image": 1, "item_name": "أرز", "quantity": 5, "unit_cost": 3}]'
    items = parse_extraction_response(text)
    assert items[0]["confidence"] == "medium"


def test_missing_barcode_becomes_none_not_empty_string():
    text = '[{"source_image": 1, "item_name": "شاي", "quantity": 5, "unit_cost": 3, "barcode": ""}]'
    items = parse_extraction_response(text)
    assert items[0]["barcode"] is None


def test_invalid_confidence_value_falls_back_to_medium():
    text = '[{"source_image": 1, "item_name": "ملح", "quantity": 5, "unit_cost": 3, "confidence": "غير معروف"}]'
    items = parse_extraction_response(text)
    assert items[0]["confidence"] == "medium"


def test_raises_when_no_json_array_found():
    with pytest.raises(OcrParseError):
        parse_extraction_response("ما قدرت أقرأ الصورة بوضوح")


def test_raises_when_json_is_malformed():
    with pytest.raises(OcrParseError):
        parse_extraction_response("[{item_name: بدون علامات تنصيص}]")


def test_raises_when_required_field_missing():
    with pytest.raises(OcrParseError):
        parse_extraction_response('[{"source_image": 1, "item_name": "صنف ناقص"}]')  # ناقص quantity/unit_cost


def test_multiple_items_from_different_source_images():
    text = """[
        {"source_image": 1, "item_name": "صنف أ", "quantity": 1, "unit_cost": 1},
        {"source_image": 2, "item_name": "صنف ب", "quantity": 2, "unit_cost": 2}
    ]"""
    items = parse_extraction_response(text)
    assert [i["source_image"] for i in items] == [1, 2]
