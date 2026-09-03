# session/session_generator.py — v6
import os
import re
import pandas as pd
from utils.categorizer import get_category
from utils.logger import get_logger

log = get_logger()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# عدد القطع بالعبوة يُستخرج من نص "الوحدة" — أولاً صيغة "كرتون 24" (كلمة عبوة + رقم،
# بدون قوسين، الصيغة الأشيع بالفواتير الحقيقية)، وإلا الصيغة القديمة "(24)" بأي مكان
# بالنص (توافق خلفي). لو ما انلقى أي رقم، نرجّع None — مو 1 ملفّق يوهم إنه قيمة حقيقية
# مؤكدة؛ الاستدعاء هو اللي يقرر قيمة افتراضية بوضوح (راجع calc_per_box).
_PER_BOX_WITH_WORD = re.compile(r"(?:كرتون|صندوق|كرتونة|بالة|جوال|شيكارة)\D{0,4}(\d+)")
_PER_BOX_PARENS = re.compile(r"\((\d+)")


def _extract_per_box_from_unit(unit: str):
    text = str(unit)
    match = _PER_BOX_WITH_WORD.search(text) or _PER_BOX_PARENS.search(text)
    return int(match.group(1)) if match else None


def generate_session_files(df_clean: pd.DataFrame, supplier_name: str = "", store_id: str = "", method: int = 1) -> tuple[str, str]:
    os.makedirs(DATA_DIR, exist_ok=True)

    # إذا تم تحديد store_id، نحفظ الملفات في مجلد المتجر
    if store_id:
        store_dir = os.path.join(DATA_DIR, store_id)
        os.makedirs(store_dir, exist_ok=True)
        invoice_path = os.path.join(store_dir, "invoice_data.xlsx")
        session_path = os.path.join(store_dir, "session_template.xlsx")
    else:
        invoice_path = os.path.join(DATA_DIR, "invoice_data.xlsx")
        session_path = os.path.join(DATA_DIR, "session_template.xlsx")

    df = df_clean.copy()

    def calc_per_box(row) -> int:
        pb = float(row.get("per_box", 0) or 0)
        if pb > 1:
            return int(pb)
        return _extract_per_box_from_unit(str(row.get("unit", "")))

    def _apply_discount(price: float, row) -> float:
        disc = float(row.get("discount_pct", 0) or 0)
        return round(price * (1 - disc), 3)

    def calc_unit_cost(row) -> float:
        try:
            # الكمية بالفاتورة = عدد قطع مفردة أصلًا (راجع ARCHITECTURE.md)، مو عدد صناديق —
            # نفس القاعدة اللي fusion/merge.py يطبّقها؛ بدون ضرب بعدد القطع بالعبوة.
            total_units = float(row.get("boxes", 0) or 0)
            total_p = _apply_discount(float(row.get("total_price", 0) or 0), row)
            cost_p = _apply_discount(float(row.get("cost_price", 0) or 0), row)
            if total_p > 0 and total_units > 0:
                return round(total_p / total_units, 3)
            if cost_p > 0:
                return round(cost_p, 3)
            return 0.0
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0

    def calc_total(row) -> float:
        try:
            total_p = _apply_discount(float(row.get("total_price", 0) or 0), row)
            if total_p > 0:
                return round(total_p, 3)
            boxes = float(row.get("boxes", 0) or 0)
            cost_p = _apply_discount(float(row.get("cost_price", 0) or 0), row)
            if boxes > 0 and cost_p > 0:
                return round(boxes * cost_p, 3)
            return 0.0
        except (TypeError, ValueError):
            return 0.0

    df["per_box_calc"] = df.apply(calc_per_box, axis=1)
    df["unit_cost"] = df.apply(calc_unit_cost, axis=1)
    df["الإجمالي"] = df.apply(calc_total, axis=1)

    # الباركود متوفّر هنا فقط بالطريقة الثانية (بعد إثراء المورد) — فاضي بالطريقة الأولى
    # (لسا ما كتبه التاجر)، وget_category يتجاهله بأمان لو فاضي.
    cats = df.apply(
        lambda r: get_category(str(r.get("item_name", "")), str(r.get("category", "")), "", str(r.get("barcode", ""))),
        axis=1,
    )
    df["التصنيف الرئيسي"] = [c[0] for c in cats]
    df["التصنيف الفرعي"] = [c[1] for c in cats]

    if supplier_name:
        df.insert(1, "المورد", supplier_name)

    # الكمية بالفاتورة = عدد قطع مفردة (مؤكد من صاحب المشروع) — القسمة على ب_الصندوق
    # تنتج رقم صناديق مرجعي، والكسور مقبولة ومتعمّدة، بدون أي تعديل.
    def calc_box_count(row) -> float:
        qty = float(row.get("boxes", 0) or 0)
        pb_raw = row.get("per_box_calc")
        # per_box_calc ممكن يكون None (غير معروف — راجع _extract_per_box_from_unit)، فلازم
        # نتحقق بـpd.isna() بدل الاعتماد على "or 1" (NaN صراحةً truthy ببايثون، تكسر int()).
        pb_int = int(pb_raw) if pb_raw and not pd.isna(pb_raw) else 1
        if pb_int > 1 and qty > 0:
            return round(qty / pb_int, 4)
        return qty

    df["الصندوق"] = df.apply(calc_box_count, axis=1)

    INV_COLS = [
        "item_id", "المورد" if supplier_name else None,
        "item_name", "التصنيف الرئيسي", "التصنيف الفرعي",
        "unit", "boxes", "per_box_calc", "الصندوق",
        "unit_cost", "الإجمالي", "expiry_date", "supplier_item_code",
    ]
    inv_cols_final = [c for c in INV_COLS if c and c in df.columns]
    df_inv = df[inv_cols_final].rename(columns={
        "item_name": "اسم الصنف", "unit": "العبوة", "boxes": "العدد",
        "per_box_calc": "ب_الصندوق", "unit_cost": "تكلفة الوحدة",
        "expiry_date": "تاريخ الصلاحية",
    })

    writer_inv = pd.ExcelWriter(invoice_path, engine="xlsxwriter")
    df_inv.to_excel(writer_inv, index=False, sheet_name="invoice_data")
    wb = writer_inv.book
    ws = writer_inv.sheets["invoice_data"]

    hdr = wb.add_format({"bold": True, "bg_color": "#0969DA", "font_color": "#FFFFFF",
                          "align": "center", "valign": "vcenter", "border": 1,
                          "font_name": "Arial", "font_size": 11})
    cell = wb.add_format({"align": "right", "valign": "vcenter", "border": 1,
                           "font_name": "Arial", "font_size": 10})
    num = wb.add_format({"align": "center", "valign": "vcenter", "border": 1,
                          "font_name": "Arial", "font_size": 10, "num_format": "#,##0.000"})
    alt = wb.add_format({"align": "right", "valign": "vcenter", "border": 1,
                          "font_name": "Arial", "font_size": 10, "bg_color": "#F6F8FA"})

    for ci, col in enumerate(df_inv.columns):
        ws.write(0, ci, col, hdr)
        ws.set_column(ci, ci, 18)
        for ri, val in enumerate(df_inv[col]):
            is_num = isinstance(val, float) and col not in ("التصنيف الرئيسي", "التصنيف الفرعي")
            fmt = num if is_num else (alt if ri % 2 == 0 else cell)
            if is_num and pd.isna(val):
                # مثلاً "ب_الصندوق" لصنف بلا معلومة عبوة بالفاتورة — فاضي فعلاً، مو 0
                # ملفّق (write_number يرفض NaN أصلاً ويطيح البرنامج لو ما تحققنا منه هنا).
                ws.write_blank(ri + 1, ci, None, fmt)
            else:
                ws.write(ri + 1, ci, val, fmt)
    writer_inv.close()

    # بناء جلسة الاستلام حسب الطريقة
    if method == 2:
        # الطريقة الثانية: واجهة مبسطة (سعر البيع فقط)
        # الباركود والصلاحية معبأة مسبقاً من مخزون المورد
        df_ses = pd.DataFrame({
            "item_id": df["item_id"],
            "الصنف": df.get("final_name", df["item_name"]),
            "الباركود": df.get("barcode", ""),
            "الصلاحية": df.get("expiration", ""),
            "سعر البيع": [""] * len(df),
        })
    else:
        # الطريقة الأولى: واجهة عادية (باركود + صلاحية + سعر البيع)
        df_ses = pd.DataFrame({
            "item_id": df["item_id"],
            "الصنف": df.get("final_name", df["item_name"]),
            "تكلفة الوحدة": df.get("unit_cost", 0),
            "الباركود": [""] * len(df),
            "الصلاحية": [""] * len(df),
            "سعر البيع": [""] * len(df),
        })

    writer_ses = pd.ExcelWriter(session_path, engine="xlsxwriter")
    df_ses.to_excel(writer_ses, index=False, sheet_name="جلسة_الاستلام")
    wb2 = writer_ses.book
    ws2 = writer_ses.sheets["جلسة_الاستلام"]

    hdr2 = wb2.add_format({"bold": True, "bg_color": "#1A7F37", "font_color": "#FFFFFF",
                            "align": "center", "valign": "vcenter", "border": 1,
                            "font_name": "Arial", "font_size": 11})
    locked = wb2.add_format({"align": "right", "valign": "vcenter", "border": 1,
                              "font_name": "Arial", "font_size": 10, "bg_color": "#F6F8FA"})
    cost_f = wb2.add_format({"align": "center", "valign": "vcenter", "border": 1,
                              "font_name": "Arial", "font_size": 10,
                              "bg_color": "#FFF8C5", "bold": True, "num_format": "#,##0.000"})
    inp = wb2.add_format({"align": "center", "valign": "vcenter", "border": 1,
                           "font_name": "Arial", "font_size": 10})
    txt_f = wb2.add_format({"align": "center", "valign": "vcenter", "border": 1,
                             "font_name": "Arial", "font_size": 10, "num_format": "@"})

    # تكوين الأعمدة حسب الطريقة
    if method == 2:
        # الطريقة الثانية: أعمدة مبسطة
        col_cfg = [
            ("item_id", 8, locked),
            ("الصنف", 36, locked),
            ("الباركود", 22, locked),
            ("الصلاحية", 15, locked),
            ("سعر البيع", 14, inp),
        ]
    else:
        # الطريقة الأولى: أعمدة كاملة
        col_cfg = [
            ("item_id", 8, locked),
            ("الصنف", 36, locked),
            ("تكلفة الوحدة", 16, cost_f),
            ("الباركود", 22, txt_f),
            ("الصلاحية", 15, inp),
            ("سعر البيع", 14, inp),
        ]

    for ci, (col, w, fmt) in enumerate(col_cfg):
        if col not in df_ses.columns:
            continue
        ws2.write(0, ci, col, hdr2)
        ws2.set_column(ci, ci, w, fmt)
        for ri, val in enumerate(df_ses[col]):
            if col in ["الباركود", "الصلاحية"] and method == 2:
                # في الطريقة الثانية، الباركود والصلاحية مقفولة (معبأة مسبقاً)
                ws2.write(ri + 1, ci, val, locked)
            elif col == "الباركود" and method == 1:
                # في الطريقة الأولى، الباركود فارغ للإدخال
                ws2.write_string(ri + 1, ci, "", txt_f)
            else:
                ws2.write(ri + 1, ci, val, fmt)
    writer_ses.close()

    log.info(f"invoice_data.xlsx → {invoice_path}")
    log.info(f"session_template.xlsx → {session_path}")
    return invoice_path, session_path
