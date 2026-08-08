# fusion/merge.py — v6
import os
import re
import pandas as pd
from utils.logger import get_logger

log = get_logger()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _extract_per_box_from_unit(unit: str) -> int:
    match = re.search(r"\((\d+)", str(unit))
    if match:
        return int(match.group(1))
    return 1


def merge_invoice_and_session() -> pd.DataFrame:
    invoice_path = os.path.join(DATA_DIR, "invoice_data.xlsx")
    session_path = os.path.join(DATA_DIR, "session_output.xlsx")

    if not os.path.exists(invoice_path):
        raise FileNotFoundError(f"invoice_data.xlsx غير موجود في {DATA_DIR}")
    if not os.path.exists(session_path):
        raise FileNotFoundError(f"session_output.xlsx غير موجود في {DATA_DIR}")

    df_inv = pd.read_excel(invoice_path)
    df_ses = pd.read_excel(session_path, dtype={"الباركود": str})

    # 🔴 إصلاح حرج: عمود "تكلفة الوحدة" موجود بالملفين، pandas يعيد تسميته لـ suffix
    # ويفشل البحث عنه صامتاً بعدين. نحذفه من جلسة التاجر لأن مصدره الحقيقي invoice_data فقط.
    df_ses = df_ses.drop(columns=["تكلفة الوحدة"], errors="ignore")

    df_inv["item_id"] = pd.to_numeric(df_inv["item_id"], errors="coerce").fillna(0).astype(int)
    df_ses["item_id"] = pd.to_numeric(df_ses["item_id"], errors="coerce").fillna(0).astype(int)

    df = pd.merge(df_inv, df_ses, on="item_id", how="left", suffixes=("_inv", "_ses"))

    for alt in ("اسم الصنف", "الصنف_inv", "الصنف"):
        if alt in df.columns and "item_name" not in df.columns:
            df = df.rename(columns={alt: "item_name"})
            break

    boxes_col = next((c for c in ["العدد", "boxes"] if c in df.columns), None)
    boxes = pd.to_numeric(df[boxes_col], errors="coerce").fillna(0) if boxes_col else pd.Series([0] * len(df))

    pb_col = next((c for c in ["ب_الصندوق", "per_box", "per_box_calc"] if c in df.columns), None)
    per_box_series = pd.to_numeric(df[pb_col], errors="coerce").fillna(0) if pb_col else pd.Series([0] * len(df))

    unit_col = next((c for c in ["العبوة", "unit"] if c in df.columns), None)

    def get_per_box(row_idx):
        pb = float(per_box_series.iloc[row_idx])
        if pb > 1:
            return int(pb)
        unit = str(df[unit_col].iloc[row_idx]) if unit_col else ""
        return _extract_per_box_from_unit(unit)

    total_units_list, num_boxes_list, per_box_list = [], [], []
    for i in range(len(df)):
        qty = float(boxes.iloc[i])
        pb_int = get_per_box(i)
        if pb_int > 1:
            total_u = qty
            n_boxes = round(qty / pb_int, 4)
        else:
            total_u = qty
            n_boxes = qty
        total_units_list.append(total_u)
        num_boxes_list.append(round(n_boxes, 2))
        per_box_list.append(pb_int)

    df["total_units"] = total_units_list
    df["num_boxes"] = num_boxes_list
    df["per_box_int"] = per_box_list

    cost_col = next((c for c in ["تكلفة الوحدة", "unit_cost"] if c in df.columns), None)
    if cost_col:
        df["unit_cost"] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)
    else:
        df["unit_cost"] = 0.0

    if (df["unit_cost"] == 0).all():
        log.warning("[تحذير حرج] كل قيم 'تكلفة الوحدة' صفر بعد الدمج! "
                    "راجع أعمدة invoice_data.xlsx و session_output.xlsx يدوياً قبل المتابعة.")

    df["سعر البيع"] = pd.to_numeric(df.get("سعر البيع", 0), errors="coerce").fillna(0)

    if "الباركود" in df.columns:
        df["الباركود"] = df["الباركود"].fillna("").astype(str).str.strip().replace("nan", "")

    if "الصلاحية" in df.columns:
        df["الصلاحية"] = df["الصلاحية"].fillna("").astype(str).str.strip()

    for cat_col in ("التصنيف الرئيسي", "التصنيف الفرعي"):
        if cat_col not in df.columns:
            df[cat_col] = ""

    log.info(f"تم الدمج: {len(df)} صنف مكتمل")
    return df
