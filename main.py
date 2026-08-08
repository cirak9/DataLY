# main.py — v6
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from extractors.excel_extractor import extract_from_excel
from transformers.base_cleaner import clean_data
from session.session_generator import generate_session_files
from fusion.reconciliation import reconcile, MasterDataError
from fusion.merge import merge_invoice_and_session
from adapters.alsahl_adapter import export_to_alsahl
from utils.validators import InvoiceValidationError
from utils.logger import get_logger

log = get_logger()

SUPPORTED_EXCEL = {".xlsx", ".xls"}
VERSION = "6.1.0"


def process_invoice(file_path: str):
    log.info("=" * 60)
    log.info(f"DataLY v{VERSION} — معالجة الفاتورة: {os.path.basename(file_path)}")
    log.info("=" * 60)

    if not os.path.exists(file_path):
        log.error(f"الملف غير موجود: {file_path}")
        return

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXCEL:
        log.error(f"نوع الملف غير مدعوم ({ext}) — الصيغ المدعومة: {SUPPORTED_EXCEL}")
        return

    try:
        raw_df, supplier = extract_from_excel(file_path)
        if raw_df.empty:
            log.error("لم يتم استخراج أي بيانات من الفاتورة")
            return

        clean_df = clean_data(raw_df)  # فيها تحقق مدمج، هترفع خطأ واضح لو فيه مشكلة
        log.info(f"{len(clean_df)} صنف صالح بعد التنظيف")

        invoice_path, session_path = generate_session_files(clean_df, supplier_name=supplier)

    except InvoiceValidationError as e:
        log.error(f"فشل التحقق من صحة البيانات: {e}")
        return

    log.info("=" * 60)
    log.info("✅ جاهز! الخطوات التالية:")
    log.info(f"   1) أرسل {os.path.basename(session_path)} للتاجر")
    log.info("   2) streamlit run session/receiving_app.py")
    log.info("   3) انقل session_output.xlsx لمجلد data/ بعد اكتمال التاجر")
    log.info("   4) python main.py --merge")
    log.info("=" * 60)


def process_merge():
    log.info("=" * 60)
    log.info(f"DataLY v{VERSION} — دمج الجلسة وتصدير ملف السهل")
    log.info("=" * 60)

    try:
        match_count = reconcile()
        if match_count:
            log.info(f"ℹ️ {match_count} تطابق عُرض للموافقة أثناء التشغيل")
        df_merged = merge_invoice_and_session()
    except (FileNotFoundError, MasterDataError) as e:
        log.error(str(e))
        return

    output_path = export_to_alsahl(df_merged)

    log.info("=" * 60)
    log.info(f"✅ اكتمل! ارفع {os.path.basename(output_path)} في شاشة 'فاتورة مشتريات' بمنظومة السهل")
    log.info("=" * 60)


def main():
    if len(sys.argv) < 2:
        print(f"DataLY v{VERSION}")
        print("الاستخدام:")
        print("  python main.py invoice.xlsx    ← معالجة فاتورة جديدة")
        print("  python main.py --merge         ← دمج جلسة التاجر وتصدير ملف السهل")
        return

    arg = sys.argv[1].strip()
    if arg == "--merge":
        process_merge()
    else:
        process_invoice(arg)


if __name__ == "__main__":
    main()
