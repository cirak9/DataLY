"""
إنشاء ملف Master Items للمتجر من ملف المخزون
يحتوي على: اسم الصنف، الباركود، الصلاحية
"""
import os
import pandas as pd
from datetime import datetime

INPUT_FILE = r"C:\Users\naji2\Downloads\اخر مخزون.xlsx"
OUTPUT_DIR = r"C:\Users\naji2\Desktop\output"

def create_master_items():
    """إنشاء ملف Master Items للمتجر"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"قراءة ملف المخزون: {INPUT_FILE}")
    df_inventory = pd.read_excel(INPUT_FILE)

    print(f"عدد الأصناف: {len(df_inventory)}")

    # استخراج الأعمدة المطلوبة
    # col_4: item_code (الباركود)
    # col_7: descR (اسم الصنف)
    # col_13: date_xp (تاريخ الصلاحية)

    master_items = []

    for idx, row in df_inventory.iterrows():
        try:
            barcode = str(row.iloc[4]).strip()
            item_name = str(row.iloc[7]).strip()
            expiry_date = row.iloc[13]

            # معالجة تاريخ الصلاحية
            if pd.notna(expiry_date):
                if isinstance(expiry_date, str):
                    expiry = expiry_date.strip()
                else:
                    # تحويل التاريخ إلى صيغة نصية
                    expiry = expiry_date.strftime("%Y-%m-%d") if hasattr(expiry_date, 'strftime') else str(expiry_date)
            else:
                expiry = ""

            # تنظيف البيانات
            barcode = barcode if barcode and barcode.lower() != "nan" else ""
            item_name = item_name if item_name and item_name.lower() != "nan" else ""
            expiry = expiry if expiry and expiry.lower() != "nan" else ""

            if barcode and item_name:  # فقط الأصناف التي تحتوي على باركود واسم
                master_items.append({
                    "اسم الصنف": item_name,
                    "الباركود": barcode,
                    "الصلاحية": expiry,
                })
        except Exception as e:
            print(f"⚠ خطأ في الصف {idx}: {e}")
            continue

    # إنشاء DataFrame
    df_master = pd.DataFrame(master_items)

    # إزالة الصفوف المكررة بناءً على الباركود
    df_master = df_master.drop_duplicates(subset=["الباركود"])

    print(f"عدد الأصناف الفريدة: {len(df_master)}")

    # حفظ في Excel
    output_path = os.path.join(OUTPUT_DIR, "master_items_متجر.xlsx")

    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    df_master.to_excel(writer, index=False, sheet_name="Master Items")
    wb = writer.book
    ws = writer.sheets["Master Items"]
    ws.right_to_left()

    # تنسيق الرؤس
    hdr = wb.add_format({
        "bold": True,
        "bg_color": "#4472C4",
        "font_color": "#FFFFFF",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 11
    })

    # تنسيق البيانات
    cell_text = wb.add_format({
        "align": "right",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10
    })

    cell_code = wb.add_format({
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10,
        "num_format": "@"
    })

    cell_date = wb.add_format({
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "font_name": "Arial",
        "font_size": 10
    })

    # تحديد عرض الأعمدة
    ws.set_column(0, 0, 40, cell_text)   # اسم الصنف
    ws.set_column(1, 1, 18, cell_code)   # الباركود
    ws.set_column(2, 2, 15, cell_date)   # الصلاحية

    # كتابة الرؤس
    ws.write(0, 0, "اسم الصنف", hdr)
    ws.write(0, 1, "الباركود", hdr)
    ws.write(0, 2, "الصلاحية", hdr)

    # كتابة البيانات
    for ri, row in df_master.iterrows():
        ws.write(ri + 1, 0, row["اسم الصنف"], cell_text)
        ws.write(ri + 1, 1, row["الباركود"], cell_code)
        ws.write(ri + 1, 2, row["الصلاحية"], cell_date)

    writer.close()

    print()
    print(f"تم الحفظ بنجاح: {output_path}")
    print()
    print("معاينة البيانات:")
    print(df_master.head(10).to_string())
    print()
    print(f"إجمالي الأصناف الفريدة: {len(df_master)}")

if __name__ == "__main__":
    create_master_items()
