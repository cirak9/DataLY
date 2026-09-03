# session/receiving_app.py
# تشغيل: streamlit run session/receiving_app.py
# دعم الطريقة الأولى والثانية

import os
import io
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def list_pending_sessions() -> list[str]:
    """
    يرجّع أسماء المتاجر (أسماء المجلدات داخل data/) اللي فيها session_template.xlsx
    بانتظار التعبئة. main.py --store <id> يكتب الملف دايماً داخل data/<id>/ (--store
    إلزامي بالأداة)، فهذا يطابق نفس المكان — بدل مسار جذر ثابت كان لا يلاقي شي أبداً.
    """
    if not os.path.isdir(DATA_DIR):
        return []
    stores = []
    for name in sorted(os.listdir(DATA_DIR)):
        store_dir = os.path.join(DATA_DIR, name)
        if os.path.isdir(store_dir) and os.path.exists(os.path.join(store_dir, "session_template.xlsx")):
            stores.append(name)
    return stores


def session_template_path(store_id: str) -> str:
    return os.path.join(DATA_DIR, store_id, "session_template.xlsx")

st.set_page_config(
    page_title="Dataly — استلام البضاعة",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main-title { font-size:26px; font-weight:700; color:#0969DA; text-align:center; margin-bottom:4px; }
  .method-badge { font-size:12px; font-weight:600; text-align:center;
                  padding:6px 12px; border-radius:8px; margin-bottom:12px;
                  display:inline-block; width:100%; }
  .method1-badge { background:#FEE2E2; color:#991B1B; }
  .method2-badge { background:#DCFCE7; color:#166534; }
  .item-name  { font-size:24px; font-weight:700; color:#0D1117; text-align:center;
                padding:14px; background:#DDF4FF; border-radius:10px; margin-bottom:12px; }
  .counter    { font-size:13px; color:#57606A; text-align:center; margin-bottom:6px; }
  .cost-box   { font-size:20px; font-weight:700; color:#9A6700; text-align:center;
                background:#FFF8C5; border-radius:8px; padding:8px 0; margin-bottom:10px; }
  .done-msg   { font-size:16px; font-weight:700; color:#1A7F37; text-align:center;
                background:#DCFFE4; border-radius:8px; padding:12px; margin:8px 0; }
  .read-only-box { background:#F3F4F6; padding:12px; border-radius:8px; margin-bottom:12px;
                   border-left:4px solid #6B7280; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_template(path: str) -> pd.DataFrame:
    return pd.read_excel(path, dtype={"item_id": int, "الباركود": str})


def detect_method(df: pd.DataFrame) -> int:
    """الكشف التلقائي عن الطريقة بناءً على البيانات في الملف"""
    # إذا كان الباركود والصلاحية معبأين → الطريقة الثانية
    # إذا كانا فارغين → الطريقة الأولى
    if df.empty:
        return 1
    first_row = df.iloc[0]
    barcode = str(first_row.get("الباركود", "")).strip()
    expiry = str(first_row.get("الصلاحية", "")).strip()
    if barcode and expiry:
        return 2
    return 1


def init_state(df: pd.DataFrame, method: int, store_id: str):
    # لو المستخدم بدّل المتجر من القائمة، نبدأ جلسة تعبئة جديدة له بدل ما نكمل ببيانات
    # المتجر السابق (كل متجر له session_template.xlsx وitem_id خاصين فيه).
    if st.session_state.get("loaded_store") != store_id:
        st.session_state.session_data = {}
        st.session_state.method = method
        st.session_state.loaded_store = store_id
        st.session_state.current_index = 0
        for _, row in df.iterrows():
            st.session_state.session_data[int(row["item_id"])] = {
                "item_id":      int(row["item_id"]),
                "الصنف":        str(row["الصنف"]),
                "تكلفة_الوحدة": float(row.get("تكلفة الوحدة", 0) or 0),
                "الباركود":     str(row.get("الباركود", "")).strip(),
                "الصلاحية":     str(row.get("الصلاحية", "")).strip(),
                "سعر البيع":    "",
                "مكتمل":        False,
            }
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0


def save_item(item_id: int, barcode: str, expiry: str, price: str, method: int):
    """حفظ بيانات الصنف حسب الطريقة"""
    e = st.session_state.session_data[item_id]

    if method == 1:
        # الطريقة الأولى: جميع الحقول قابلة للتعديل
        e["الباركود"]  = barcode.strip()
        e["الصلاحية"]  = expiry.strip()
        e["سعر البيع"] = price.strip()
        e["مكتمل"]     = bool(barcode.strip() and expiry.strip() and price.strip())
    else:
        # الطريقة الثانية: فقط سعر البيع قابل للتعديل
        e["سعر البيع"] = price.strip()
        e["مكتمل"]     = bool(e["الباركود"] and e["الصلاحية"] and price.strip())


def build_excel_bytes() -> bytes:
    rows = list(st.session_state.session_data.values())
    df_out = pd.DataFrame(rows)[[
        "item_id", "الصنف", "الباركود", "الصلاحية", "سعر البيع", "مكتمل"
    ]]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False, sheet_name="session_output")
        wb = writer.book
        ws = writer.sheets["session_output"]
        hdr  = wb.add_format({"bold": True, "bg_color": "#1A7F37", "font_color": "#FFFFFF",
                               "align": "center", "border": 1, "font_name": "Arial"})
        cell = wb.add_format({"align": "center", "border": 1, "font_name": "Arial"})
        txt  = wb.add_format({"align": "center", "border": 1, "font_name": "Arial", "num_format": "@"})
        widths = [8, 34, 20, 14, 12, 10]
        for ci, (col, w) in enumerate(zip(df_out.columns, widths)):
            ws.write(0, ci, col, hdr)
            ws.set_column(ci, ci, w, txt if ci == 2 else cell)
        for ri, row in df_out.iterrows():
            for ci, col in enumerate(df_out.columns):
                fmt = txt if ci == 2 else cell
                ws.write(ri + 1, ci, row[col], fmt)
    buf.seek(0)
    return buf.read()


def main():
    stores = list_pending_sessions()
    if not stores:
        st.error("❌ لم يتم العثور على أي ملف جلسة بمجلد data/<اسم_المتجر>/. شغّل main.py أولاً.")
        return

    if len(stores) == 1:
        store_id = stores[0]
    else:
        store_id = st.selectbox("🏬 اختر المتجر", stores, key="store_selector")

    df = load_template(session_template_path(store_id))
    method = detect_method(df)
    init_state(df, method, store_id)

    items      = list(st.session_state.session_data.values())
    total      = len(items)
    done_count = sum(1 for it in items if it["مكتمل"])
    all_done   = done_count == total

    # ── رأس الصفحة ───────────────────────────────────────────────
    st.markdown('<div class="main-title">📦 Dataly — استلام البضاعة</div>',
                unsafe_allow_html=True)

    # عرض نوع الطريقة
    if method == 1:
        st.markdown('<div class="method-badge method1-badge">الطريقة الأولى — إدخال يدوي (باركود + صلاحية + سعر)</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="method-badge method2-badge">⚡ الطريقة الثانية — إدخال سريع (سعر فقط)</div>',
                    unsafe_allow_html=True)

    st.progress(done_count / total if total > 0 else 0)
    st.markdown(f'<div class="counter">✅ {done_count} من {total} صنف مكتمل</div>',
                unsafe_allow_html=True)
    st.divider()

    # ── القائمة الجانبية ─────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📋 اختيار سريع")
        for idx, it in enumerate(items):
            badge = "✅" if it["مكتمل"] else "⬜"
            if st.button(
                f"{badge}  {it['الصنف'][:28]}",
                key=f"sb_{it['item_id']}",
                use_container_width=True,
            ):
                st.session_state.current_index = idx
                st.rerun()

    # ── الصنف الحالي ─────────────────────────────────────────────
    idx          = st.session_state.current_index
    current_item = items[idx]
    item_id      = current_item["item_id"]
    unit_cost    = current_item["تكلفة_الوحدة"]

    st.markdown(f'<div class="counter">الصنف {idx + 1} من {total}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="item-name">{current_item["الصنف"]}</div>',
                unsafe_allow_html=True)

    if unit_cost > 0:
        st.markdown(
            f'<div class="cost-box">💰 تكلفة الوحدة: {unit_cost:,.3f} د.ل</div>',
            unsafe_allow_html=True,
        )

    # ── نموذج الإدخال (يختلف حسب الطريقة) ────────────────────────
    with st.form(key=f"frm_{item_id}", clear_on_submit=False):

        if method == 1:
            # الطريقة الأولى: حقول قابلة للتعديل
            barcode = st.text_input(
                "🔍 الباركود",
                value=current_item["الباركود"],
                placeholder="امسح الباركود...",
                key=f"bc_{item_id}",
            )
            expiry = st.text_input(
                "📅 الصلاحية (MM/YYYY)",
                value=current_item["الصلاحية"],
                placeholder="مثال: 06/2027",
                key=f"exp_{item_id}",
            )
        else:
            # الطريقة الثانية: عرض البيانات المعبأة (read-only)
            barcode = current_item["الباركود"]
            expiry = current_item["الصلاحية"]

            st.markdown(f"""
            <div class="read-only-box">
                <strong>🔍 الباركود:</strong> {barcode}<br>
                <strong>📅 الصلاحية:</strong> {expiry}
            </div>
            """, unsafe_allow_html=True)

        # حقل سعر البيع (يظهر دائماً)
        price = st.text_input(
            "🏷️ سعر البيع (د.ل)",
            value=current_item["سعر البيع"],
            placeholder="أدخل سعر البيع...",
            key=f"pr_{item_id}",
        )

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            prev = st.form_submit_button("◀ السابق", use_container_width=True)
        with c2:
            save_next = st.form_submit_button(
                "حفظ والتالي ▶", use_container_width=True, type="primary"
            )
        with c3:
            save_only = st.form_submit_button("💾 حفظ", use_container_width=True)

        if save_next or save_only:
            save_item(item_id, barcode, expiry, price, method)
            done_count = sum(1 for it in st.session_state.session_data.values() if it["مكتمل"])
            if save_next and idx < total - 1:
                st.session_state.current_index = idx + 1
                st.rerun()
            elif save_next and idx == total - 1:
                st.rerun()
            else:
                st.success("✅ تم الحفظ")

        if prev and idx > 0:
            save_item(item_id, barcode, expiry, price, method)
            st.session_state.current_index = idx - 1
            st.rerun()

    # ── زر التحميل — يظهر فقط عند اكتمال جميع الأصناف ───────────
    st.divider()
    done_now = sum(1 for it in st.session_state.session_data.values() if it["مكتمل"])

    if done_now < total:
        remaining = total - done_now
        st.info(f"⏳ تبقى {remaining} صنف — أكمل التعبئة لتفعيل زر التحميل.")
    else:
        st.markdown(
            '<div class="done-msg">🎉 اكتملت جميع الأصناف — الملف جاهز!</div>',
            unsafe_allow_html=True,
        )
        st.info(f"📁 بعد التحميل، انقل الملف يدوياً لمجلد: data/{store_id}/session_output.xlsx")

        excel_bytes = build_excel_bytes()

        c_dl, c_wa = st.columns(2)

        with c_dl:
            st.download_button(
                label="📥 تحميل session_output.xlsx",
                data=excel_bytes,
                file_name="session_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )

if __name__ == "__main__":
    main()
