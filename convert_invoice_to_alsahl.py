"""
تحويل فاتورة سهلة إلى صيغة السهل (Alsahl)
بدون الحاجة إلى session
"""
import os
import pandas as pd
from datetime import datetime

# مسار الملف المراد تحويله
INPUT_FILE = r"C:\Users\naji2\Desktop\شركة_النيل_الذهبية_Invoice.xlsx"
OUTPUT_DIR = r"C:\Users\naji2\Desktop\output"

def convert_invoice_to_alsahl():
    """تحويل الفاتورة إلى صيغة السهل"""

    # إنشاء مجلد الإخراج
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # قراءة الملف
    print(f"قراءة الملف: {INPUT_FILE}")
    df_input = pd.read_excel(INPUT_FILE)

    print(f"عدد الصفوف: {len(df_input)}")
    print(f"أسماء الأعمدة (الأرقام): {list(range(len(df_input.columns)))}")

    # تحديد أسماء الأعمدة بناءً على الموضع
    # بناءً على البيانات التي رأيناها:
    # col 0: الباركود
    # col 1: اسم المنتج
    # col 2: العبوة (عدد القطع)
    # col 3: العدد الإجمالي
    # col 4: التكلفة للوحدة
    # col 5: سعر البيع
    # col 6: الصلاحية
    # col 7: المورد
    # col 8, 9: ربما التصنيفات (سنرك الأعمدة الفارغة)

    col_map = {
        'barcode': 0,      # الكود/الباركود
        'item_name': 1,    # الوصف
        'per_box': 2,      # العبوة
        'total_units': 3,  # العدد
        'unit_cost': 4,    # التكلفة
        'sale_price': 5,   # البيع
        'expiry': 6,       # الصلاحية
        'supplier': 7,     # المورد
        'sub_cat': 8,      # التصنيف الفرعي (تم عكسه)
        'main_cat': 9,     # التصنيف الرئيسي (تم عكسه)
    }

    rows = []
    for idx, row in df_input.iterrows():
        try:
            barcode = str(row.iloc[col_map['barcode']]).strip()
            item_name = str(row.iloc[col_map['item_name']]).strip()
            per_box = int(row.iloc[col_map['per_box']] or 1)
            total_units = float(row.iloc[col_map['total_units']] or 0)
            unit_cost = float(row.iloc[col_map['unit_cost']] or 0)
            sale_price = float(row.iloc[col_map['sale_price']] or 0)
            expiry = str(row.iloc[col_map['expiry']]).strip() if pd.notna(row.iloc[col_map['expiry']]) else ""
            supplier = str(row.iloc[col_map['supplier']]).strip() if pd.notna(row.iloc[col_map['supplier']]) else ""
            main_cat = str(row.iloc[col_map['main_cat']]).strip() if pd.notna(row.iloc[col_map['main_cat']]) else ""
            sub_cat = str(row.iloc[col_map['sub_cat']]).strip() if pd.notna(row.iloc[col_map['sub_cat']]) else ""

            # تنظيف البيانات
            barcode = barcode if barcode and barcode.lower() != "nan" else ""
            expiry = expiry if expiry and expiry.lower() != "nan" else ""
            supplier = supplier if supplier and supplier.lower() != "nan" else ""

            # حساب سعر الصندوق = التكلفة × عدد القطع بالعبوة
            box_price = unit_cost * per_box

            rows.append({
                "الكود": barcode,
                "الوصف": item_name,
                "العبوة": per_box,
                "العدد": total_units,
                "التكلفة": unit_cost,
                "البيع": sale_price,
                "الصلاحية": expiry,
                "المورد": supplier,
                "فرعي": sub_cat,
                "رئيسي": main_cat,
                "الصندوق": barcode,      # كود الصندوق = الباركود
                "ب_الصندوق": box_price,  # سعر الصندوق = التكلفة × العبوة
            })
        except Exception as e:
            print(f"⚠️ خطأ في الصف {idx}: {e}")
            continue

    # إنشاء DataFrame بالصيغة الجديدة
    COL_ORDER = ["الكود", "الوصف", "العبوة", "العدد", "التكلفة", "البيع",
                 "الصلاحية", "المورد", "فرعي", "رئيسي", "الصندوق", "ب_الصندوق"]
    df_out = pd.DataFrame(rows)[COL_ORDER]

    # حفظ في Excel
    output_path = os.path.join(OUTPUT_DIR, "output_alsahl.xlsx")

    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    df_out.to_excel(writer, index=False, sheet_name="فاتورة مشتريات")
    wb = writer.book
    ws = writer.sheets["فاتورة مشتريات"]
    ws.right_to_left()

    # تنسيق الخلايا
    hdr = wb.add_format({
        "bold": True,
        "bg_color": "#FFC000",
        "font_color": "#0D1117",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 11
    })

    cell = wb.add_format({
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10
    })

    txt = wb.add_format({
        "align": "right",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10
    })

    bc_fmt = wb.add_format({
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10,
        "num_format": "@"
    })

    num_fmt = wb.add_format({
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10,
        "num_format": "#,##0.000"
    })

    # تحديد عرض الأعمدة
    WIDTHS = {
        "الكود": 18,
        "الوصف": 34,
        "العبوة": 16,
        "العدد": 10,
        "التكلفة": 13,
        "البيع": 13,
        "الصلاحية": 16,
        "المورد": 22,
        "فرعي": 18,
        "رئيسي": 20,
        "الصندوق": 12,
        "ب_الصندوق": 12
    }

    # تطبيق التنسيق على الرؤوس والأعمدة
    for ci, col in enumerate(COL_ORDER):
        ws.write(0, ci, col, hdr)
        w = WIDTHS.get(col, 14)

        # اختيار التنسيق المناسب للعمود
        if col == "الكود":
            fmt = bc_fmt
        elif col in ("التكلفة", "البيع", "العدد", "العبوة"):
            fmt = num_fmt
        elif col == "الوصف":
            fmt = txt
        else:
            fmt = cell

        ws.set_column(ci, ci, w, fmt)

    # كتابة البيانات
    for ri, row in df_out.iterrows():
        for ci, col in enumerate(COL_ORDER):
            val = row[col]

            if col == "الكود":
                ws.write_string(ri + 1, ci, str(val), bc_fmt)
            elif col in ("التكلفة", "البيع", "العدد", "العبوة"):
                num_val = float(val) if str(val) not in ("", "nan") else 0
                ws.write_number(ri + 1, ci, num_val, num_fmt)
            elif col == "الوصف":
                ws.write(ri + 1, ci, val, txt)
            else:
                ws.write(ri + 1, ci, val, cell)

    writer.close()

    print()
    print(f"تم الحفظ بنجاح: {output_path}")
    print(f"عدد الأصناف: {len(df_out)}")
    print()
    print("معاينة البيانات:")
    print(df_out.head(5).to_string())

if __name__ == "__main__":
    convert_invoice_to_alsahl()
