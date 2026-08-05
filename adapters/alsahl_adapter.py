# adapters/alsahl_adapter.py — v6
import os
import pandas as pd
from utils.categorizer import get_category as _get_category_util
from utils.logger import get_logger

log = get_logger()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def export_to_alsahl(df_merged: pd.DataFrame, supplier_name: str = "") -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "output_alsahl.xlsx")

    rows = []
    for _, row in df_merged.iterrows():
        item_name = str(row.get("item_name", "")).strip()
        cat_main = str(row.get("التصنيف الرئيسي", "")).strip()
        cat_sub = str(row.get("التصنيف الفرعي", "")).strip()
        main_cat, sub_cat = _get_category_util(item_name, cat_main, cat_sub)

        unit = str(row.get("العبوة", row.get("unit", ""))).strip()
        unit = unit if unit.lower() not in ("nan", "") else ""

        total_units = float(row.get("total_units", 0) or 0)
        num_boxes = float(row.get("num_boxes", 0) or 0)
        per_box_int = int(row.get("per_box_int", 1) or 1)

        unit_cost = float(row.get("unit_cost", 0) or 0)
        sale_price = float(row.get("سعر البيع", 0) or 0)

        barcode = str(row.get("الباركود", "")).strip()
        if not barcode or barcode.lower() == "nan":
            barcode = str(row.get("supplier_item_code", "")).strip()
        barcode = barcode if barcode and barcode.lower() not in ("nan", "") else ""

        expiry = str(row.get("الصلاحية", "")).strip()
        expiry = expiry if expiry and expiry.lower() != "nan" else ""

        supplier = supplier_name or str(row.get("المورد", "")).strip()
        supplier = supplier if supplier and supplier.lower() != "nan" else ""

        rows.append({
            "الكود": barcode, "الوصف": item_name, "العبوة": unit,
            "العدد": total_units, "التكلفة": unit_cost, "البيع": sale_price,
            "الصلاحية": expiry, "المورد": supplier, "فرعي": sub_cat,
            "رئيسي": main_cat, "الصندوق": num_boxes, "ب_الصندوق": per_box_int,
        })

    COL_ORDER = ["الكود", "الوصف", "العبوة", "العدد", "التكلفة", "البيع",
                 "الصلاحية", "المورد", "فرعي", "رئيسي", "الصندوق", "ب_الصندوق"]
    df_out = pd.DataFrame(rows)[COL_ORDER]

    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    df_out.to_excel(writer, index=False, sheet_name="فاتورة مشتريات")
    wb = writer.book
    ws = writer.sheets["فاتورة مشتريات"]
    ws.right_to_left()

    hdr = wb.add_format({"bold": True, "bg_color": "#FFC000", "font_color": "#0D1117",
                          "align": "center", "valign": "vcenter", "border": 1,
                          "font_name": "Arial", "font_size": 11})
    cell = wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "font_name": "Arial", "font_size": 10})
    txt = wb.add_format({"align": "right", "valign": "vcenter", "border": 1, "font_name": "Arial", "font_size": 10})
    bc_fmt = wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "font_name": "Arial", "font_size": 10, "num_format": "@"})
    num_fmt = wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "font_name": "Arial", "font_size": 10, "num_format": "#,##0.000"})

    WIDTHS = {"الكود": 18, "الوصف": 34, "العبوة": 16, "العدد": 10, "التكلفة": 13,
              "البيع": 13, "الصلاحية": 16, "المورد": 22, "فرعي": 18, "رئيسي": 20,
              "الصندوق": 12, "ب_الصندوق": 12}

    for ci, col in enumerate(COL_ORDER):
        ws.write(0, ci, col, hdr)
        w = WIDTHS.get(col, 14)
        fmt = bc_fmt if col == "الكود" else (
            num_fmt if col in ("التكلفة", "البيع", "العدد", "الصندوق", "ب_الصندوق") else (
                txt if col == "الوصف" else cell))
        ws.set_column(ci, ci, w, fmt)

    for ri, row in df_out.iterrows():
        for ci, col in enumerate(COL_ORDER):
            val = row[col]
            if col == "الكود":
                ws.write_string(ri + 1, ci, str(val), bc_fmt)
            elif col in ("التكلفة", "البيع", "العدد", "الصندوق", "ب_الصندوق"):
                ws.write_number(ri + 1, ci, float(val) if str(val) not in ("", "nan") else 0, num_fmt)
            elif col == "الوصف":
                ws.write(ri + 1, ci, val, txt)
            else:
                ws.write(ri + 1, ci, val, cell)

    writer.close()
    log.info(f"output_alsahl.xlsx → {output_path} ({len(df_out)} صنف)")
    return output_path
