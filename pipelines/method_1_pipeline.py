"""
خط الطريقة الأولى:
1. قراءة مخزون المتجر
2. قراءة الفاتورة
3. مطابقة الأصناف مع المخزون
4. توليد جلسة الاستلام
5. دمج الجلسة مع الفاتورة
6. تحديث جرد المخزون
7. التصدير لمنظومة السهل
"""

import os
from extractors.excel_extractor import extract_from_excel
from extractors.inventory_extractor import extract_old_inventory
from transformers.base_cleaner import clean_data
from fusion.inventory_manager import InventoryManager
from fusion.inventory_matcher import (
    match_invoice_with_inventory,
    resolve_matches_interactively,
    apply_resolutions
)
from session.session_generator import generate_session_files
from fusion.merge import merge_invoice_and_session
from adapters.alsahl_adapter import export_to_alsahl
from utils.logger import get_logger
from utils.validators import InvoiceValidationError

log = get_logger()


def run_method_1(store_id: str, inventory_path: str, invoice_path: str):
    """
    تشغيل الطريقة الأولى

    Args:
        store_id: معرف المتجر (مثل store_1)
        inventory_path: مسار ملف المخزون القديم
        invoice_path: مسار ملف الفاتورة
    """

    log.info("")
    log.info("=" * 80)
    log.info(f"🔵 الطريقة الأولى — المتجر: {store_id}")
    log.info("=" * 80)

    try:
        # الخطوة 1: قراءة المخزون القديم
        log.info("\n[1/7] قراءة مخزون المتجر القديم...")
        old_inventory = extract_old_inventory(inventory_path)

        # الخطوة 2: قراءة الفاتورة
        log.info("[2/7] قراءة الفاتورة...")
        raw_invoice, supplier = extract_from_excel(invoice_path)

        if raw_invoice.empty:
            log.error("لم يتم استخراج أي بيانات من الفاتورة")
            return

        # الخطوة 3: تنظيف الفاتورة
        log.info("[3/7] تنظيف بيانات الفاتورة...")
        clean_invoice = clean_data(raw_invoice)
        log.info(f"   {len(clean_invoice)} صنف صالح بعد التنظيف")

        # الخطوة 4: مطابقة الأصناف
        log.info("[4/7] مطابقة الأصناف مع مخزون المتجر...")
        matched_invoice, matches = match_invoice_with_inventory(clean_invoice, old_inventory)

        # الخطوة 5: طلب الموافقة اليدوية (إن وجدت تطابقات)
        if matches:
            log.info("[5/7] طلب الموافقة اليدوية على التطابقات...")
            resolutions = resolve_matches_interactively(matches)
            matched_invoice = apply_resolutions(matched_invoice, resolutions)
        else:
            log.info("[5/7] لا توجد تطابقات، استخدام أسماء الفاتورة")

        # الخطوة 6: توليد جلسة الاستلام
        log.info("[6/7] توليد جلسة الاستلام...")
        session_path = generate_session_files(
            matched_invoice,
            supplier_name=supplier,
            store_id=store_id,
            method=1
        )[1]

        log.info("")
        log.info("=" * 80)
        log.info("✅ اكتملت الخطوات:")
        log.info(f"   ✓ تم قراءة المخزون")
        log.info(f"   ✓ تم مطابقة الأصناف")
        log.info(f"   ✓ تم توليد جلسة الاستلام")
        log.info("")
        log.info(f"📝 الخطوات التالية:")
        log.info(f"   1) أرسل {os.path.basename(session_path)} للتاجر")
        log.info(f"   2) streamlit run session/receiving_app.py")
        log.info(f"   3) انقل session_output.xlsx لمجلد data/{store_id}/ بعد اكتمال التاجر")
        log.info(f"   4) python main.py --merge --store {store_id}")
        log.info("=" * 80)

    except InvoiceValidationError as e:
        log.error(f"❌ فشل التحقق من صحة البيانات: {e}")
        return
    except Exception as e:
        log.error(f"❌ خطأ: {e}")
        raise
