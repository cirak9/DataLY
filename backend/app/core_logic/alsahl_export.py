# منقول شبه حرفي من adapters/alsahl_adapter.py بالأداة الأصلية — نفس ترتيب الأعمدة،
# التنسيق، وقاعدة "فاضي لو غير معروف" بالضبط (Alsahl POS يقرأ هذي الصيغة تحديداً، مو
# اجتهاد داخلي — تغيير الترتيب/الأسماء يكسر الاستيراد فعلياً). دالة نصية بحتة بمعزل عن
# أي DB: تاخذ list[dict] جاهزة وترجّع bytes الملف. راجع docs/REBUILD_PLAN.md قسم 2.
import io

import pandas as pd

COL_ORDER = ["الكود", "الوصف", "العبوة", "العدد", "التكلفة", "البيع",
             "الصلاحية", "المورد", "فرعي", "رئيسي", "الصندوق", "ب_الصندوق"]

_WIDTHS = {"الكود": 18, "الوصف": 34, "العبوة": 16, "العدد": 10, "التكلفة": 13,
           "البيع": 13, "الصلاحية": 16, "المورد": 22, "فرعي": 18, "رئيسي": 20,
           "الصندوق": 12, "ب_الصندوق": 12}


def build_alsahl_workbook(rows: list[dict]) -> bytes:
    """
    rows: كل عنصر بالترتيب COL_ORDER بالضبط، القيم الرقمية أرقام حقيقية (مو نصوص)،
    و"العبوة" إما int أو "" (فاضي = عدد القطع بالعبوة غير معروف فعلاً — نتركها فاضية
    بالإكسل (write_blank) بدل ما نكتب 0 أو 1 يوهمان إنهما قيمة مؤكدة).
    """
    df_out = pd.DataFrame(rows, columns=COL_ORDER)

    buf = io.BytesIO()
    writer = pd.ExcelWriter(buf, engine="xlsxwriter")
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

    for ci, col in enumerate(COL_ORDER):
        ws.write(0, ci, col, hdr)
        w = _WIDTHS.get(col, 14)
        fmt = bc_fmt if col == "الكود" else (
            num_fmt if col in ("التكلفة", "البيع", "العدد", "العبوة") else (
                txt if col == "الوصف" else cell))
        ws.set_column(ci, ci, w, fmt)

    for ri, row in df_out.iterrows():
        for ci, col in enumerate(COL_ORDER):
            val = row[col]
            if col == "الكود":
                ws.write_string(ri + 1, ci, str(val), bc_fmt)
            elif col == "العبوة":
                if val == "" or (isinstance(val, float) and pd.isna(val)):
                    ws.write_blank(ri + 1, ci, None, num_fmt)
                else:
                    ws.write_number(ri + 1, ci, float(val), num_fmt)
            elif col in ("التكلفة", "البيع", "العدد"):
                ws.write_number(ri + 1, ci, float(val) if str(val) not in ("", "nan") else 0, num_fmt)
            elif col == "الوصف":
                ws.write(ri + 1, ci, val, txt)
            else:
                ws.write(ri + 1, ci, val, cell)

    writer.close()
    buf.seek(0)
    return buf.read()
