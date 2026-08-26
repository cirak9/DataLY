"""
خط الطريقة الثانية:
1. قراءة مخزون المتجر
2. قراءة الفاتورة
3. قراءة مخزون المورد
4. إثراء الفاتورة من مخزون المورد
5. مطابقة الفاتورة المُثرية مع مخزون المتجر
6. توليد جلسة استلام مبسطة
7. دمج الجلسة مع الفاتورة
8. تحديث جرد المخزون
9. التصدير لمنظومة السهل
"""

import os
from extractors.excel_extractor import extract_from_excel
from extractors.inventory_extractor import extract_old_inventory, extract_supplier_inventory
from transformers.base_cleaner import clean_data
from fusion.inventory_manager import InventoryManager
from fusion.supplier_matcher import (
    enrich_invoice_from_supplier,
    match_enriched_invoice_with_inventory,
    resolve_method2_matches_interactively
)
from session.session_generator import generate_session_files
from fusion.merge import merge_invoice_and_session
from adapters.alsahl_adapter import export_to_alsahl
from utils.logger import get_logger
from utils.validators import InvoiceValidationError

log = get_logger()


def run_method_2(store_id: str, inventory_path: str, invoice_path: str, supplier_path: str):
    """
    تشغيل الطريقة الثانية

    Args:
        store_id: معرف المتجر
        inventory_path: مسار ملف المخزون القديم
        invoice_path: مسار ملف الفاتورة
        supplier_path: مسار ملف مخزون المورد
    """

    log.info("")
    log.info("=" * 80)
    log.info(f"🟢 الطريقة الثانية — المتجر: {store_id}")
    log.info("=" * 80)

    try:
        # الخطوة 1: قراءة المخزون القديم
        log.info("\n[1/9] قراءة مخزون المتجر القديم...")
        old_inventory = extract_old_inventory(inventory_path)

        # الخطوة 2: قراءة الفاتورة
        log.info("[2/9] قراءة الفاتورة...")
        raw_invoice, supplier = extract_from_excel(invoice_path)

        if raw_invoice.empty:
            log.error("لم يتم استخراج أي بيانات من الفاتورة")
            return

        # الخطوة 3: تنظيف الفاتورة
        log.info("[3/9] تنظيف بيانات الفاتورة...")
        clean_invoice = clean_data(raw_invoice)
        log.info(f"   {len(clean_invoice)} صنف صالح بعد التنظيف")

        # الخطوة 4: قراءة مخزون المورد
        log.info("[4/9] قراءة مخزون المورد...")
        supplier_inventory = extract_supplier_inventory(supplier_path)
        log.info(f"   {len(supplier_inventory)} صنف في مخزون المورد")

        # الخطوة 5: إثراء الفاتورة من مخزون المورد
        log.info("[5/9] إثراء الفاتورة بالباركود والصلاحية من مخزون المورد...")
        enriched_invoice, enrichment_issues = enrich_invoice_from_supplier(
            clean_invoice,
            supplier_inventory
        )

        if enrichment_issues:
            log.warning(f"   ⚠️ {len(enrichment_issues)} صنف لم يتم إثراؤه من المورد (أصناف جديدة)")

        # الخطوة 6: مطابقة الفاتورة المُثرية مع مخزون المتجر
        log.info("[6/9] مطابقة الأصناف مع مخزون المتجر...")
        matched_invoice, matches = match_enriched_invoice_with_inventory(
            enriched_invoice,
            old_inventory
        )

        # الخطوة 7: طلب الموافقة اليدوية (إن وجدت تطابقات)
        if matches:
            log.info("[7/9] طلب الموافقة اليدوية على التطابقات...")
            resolutions = resolve_method2_matches_interactively(matches)
            for idx, final_name in resolutions.items():
                matched_invoice.at[idx, 'final_name'] = final_name
        else:
            log.info("[7/9] لا توجد تطابقات إضافية")

        # الخطوة 8: توليد جلسة الاستلام المبسطة
        log.info("[8/9] توليد جلسة استلام مبسطة (سعر البيع فقط)...")
        session_path = generate_session_files(
            matched_invoice,
            supplier_name=supplier,
            store_id=store_id,
            method=2
        )[1]

        log.info("")
        log.info("=" * 80)
        log.info("✅ اكتملت الخطوات:")
        log.info(f"   ✓ تم قراءة المخزون والمورد")
        log.info(f"   ✓ تم إثراء الفاتورة")
        log.info(f"   ✓ تم مطابقة الأصناف")
        log.info(f"   ✓ تم توليد جلسة الاستلام المبسطة")
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
