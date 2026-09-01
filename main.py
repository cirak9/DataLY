# main.py — v7 (دعم الطريقة الأولى والثانية)
import sys
import os
import argparse

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from fusion.method_router import detect_method
from pipelines.method_1_pipeline import run_method_1
from pipelines.method_2_pipeline import run_method_2
from fusion.reconciliation import reconcile, MasterDataError
from fusion.merge import merge_invoice_and_session
from fusion.inventory_manager import InventoryManager
from adapters.alsahl_adapter import export_to_alsahl
from utils.logger import get_logger

log = get_logger()

SUPPORTED_EXCEL = {".xlsx", ".xls"}
VERSION = "7.0.0"


def process_invoice(store_id: str, inventory_path: str, invoice_path: str, supplier_path: str = None, method_override: int = None):
    """
    معالجة الفاتورة حسب الطريقة (الأولى أو الثانية)
    """
    if not os.path.exists(invoice_path):
        log.error(f"الملف غير موجود: {invoice_path}")
        return

    ext = os.path.splitext(invoice_path)[1].lower()
    if ext not in SUPPORTED_EXCEL:
        log.error(f"نوع الملف غير مدعوم ({ext}) — الصيغ المدعومة: {SUPPORTED_EXCEL}")
        return

    # تحديد الطريقة
    method = detect_method(supplier_path, method_override)

    try:
        if method == 1:
            run_method_1(store_id, inventory_path, invoice_path)
        else:
            if not supplier_path:
                log.error("الطريقة الثانية تتطلب ملف مخزون المورد (--supplier)")
                return
            run_method_2(store_id, inventory_path, invoice_path, supplier_path)

    except Exception as e:
        log.error(f"❌ خطأ أثناء المعالجة: {e}")
        raise


def process_merge(store_id: str):
    """
    دمج جلسة الاستلام والتصدير لمنظومة السهل
    """
    log.info("=" * 80)
    log.info(f"🔄 دمج الجلسة وتصدير ملف السهل — المتجر: {store_id}")
    log.info("=" * 80)

    try:
        match_count = reconcile(store_id)
        if match_count:
            log.info(f"ℹ️ {match_count} تطابق عُرض للموافقة أثناء التشغيل")

        df_merged = merge_invoice_and_session(store_id)
        output_path = export_to_alsahl(df_merged, store_id=store_id)

        # تحديث جرد المخزون
        log.info("\n📊 تحديث جرد المخزون...")
        inventory_mgr = InventoryManager(store_id)
        old_inventory = inventory_mgr.load_old_inventory()
        updated_inventory = inventory_mgr.update_inventory(old_inventory, df_merged)
        inventory_mgr.save_updated_inventory(updated_inventory)

        log.info("=" * 80)
        log.info(f"✅ اكتمل! ارفع {os.path.basename(output_path)} في شاشة 'فاتورة مشتريات' بمنظومة السهل")
        log.info("=" * 80)

    except (FileNotFoundError, MasterDataError) as e:
        log.error(str(e))
        return


def main():
    if len(sys.argv) < 2:
        print(f"DataLY v{VERSION}")
        print("")
        print("الاستخدام:")
        print("")
        print("  الطريقة الأولى (مخزون المتجر فقط):")
        print("    python main.py \\")
        print("      --store store_1 \\")
        print("      --inventory data/store_1/old_inventory.xlsx \\")
        print("      --invoice data/store_1/invoice.xlsx")
        print("")
        print("  الطريقة الثانية (مع مخزون المورد):")
        print("    python main.py \\")
        print("      --store store_1 \\")
        print("      --inventory data/store_1/old_inventory.xlsx \\")
        print("      --invoice data/store_1/invoice.xlsx \\")
        print("      --supplier data/store_1/supplier_inventory.xlsx")
        print("")
        print("  إجبار طريقة معينة:")
        print("    python main.py \\")
        print("      --store store_1 \\")
        print("      --inventory data/store_1/old_inventory.xlsx \\")
        print("      --invoice data/store_1/invoice.xlsx \\")
        print("      --method 1")
        print("")
        print("  الدمج والتصدير:")
        print("    python main.py --merge --store store_1")
        print("")
        return

    parser = argparse.ArgumentParser(description="DataLY — معالجة فواتير الموردين")
    parser.add_argument("--store", required=False, help="معرف المتجر (store_1, store_2, ...)")
    parser.add_argument("--inventory", help="مسار ملف المخزون القديم")
    parser.add_argument("--invoice", help="مسار ملف الفاتورة")
    parser.add_argument("--supplier", help="مسار ملف مخزون المورد (اختياري)")
    parser.add_argument("--method", type=int, choices=[1, 2], help="فرض طريقة معينة (1 أو 2)")
    parser.add_argument("--merge", action="store_true", help="دمج وتصدير")

    args = parser.parse_args()

    if args.merge:
        if not args.store:
            log.error("--merge تتطلب --store")
            return
        process_merge(args.store)
    else:
        if not all([args.store, args.inventory, args.invoice]):
            log.error("معالجة الفاتورة تتطلب: --store, --inventory, --invoice")
            return
        process_invoice(args.store, args.inventory, args.invoice, args.supplier, args.method)


if __name__ == "__main__":
    main()
