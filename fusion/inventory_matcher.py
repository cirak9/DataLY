import pandas as pd
from typing import Tuple, List
from utils.logger import get_logger

log = get_logger()


def match_invoice_with_inventory(invoice_df: pd.DataFrame, old_inventory: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """
    مطابقة أصناف الفاتورة مع مخزون المتجر (الطريقة الأولى)

    يبحث عن الباركود في المخزون:
    - إذا موجود: يحتاج موافقة يدوية على الاسم
    - إذا غير موجود: يستخدم اسم الفاتورة مباشرة

    Args:
        invoice_df: بيانات الفاتورة
        old_inventory: بيانات المخزون القديم

    Returns:
        (df_with_matched_names, matches_needing_approval)
    """

    # نسخة من الفاتورة للعمل عليها
    result_df = invoice_df.copy()
    matches_requiring_approval = []

    # إعادة تسمية عمود الاسم إذا لم يكن موجود
    # عمود الاسم القياسي بعد transformers/base_cleaner.py اسمه item_name، مو name.
    if 'final_name' not in result_df.columns:
        result_df['final_name'] = result_df.get('item_name', '')

    # للتكامل مع الكود الموجود، نتحقق من عمود الباركود
    barcode_col = 'barcode' if 'barcode' in result_df.columns else 'code'

    for idx, row in result_df.iterrows():
        invoice_barcode = str(row.get(barcode_col, '')).strip()
        invoice_name = str(row.get('item_name', '')).strip()

        if not invoice_barcode:
            log.warning(f"صنف بدون باركود (الصف {idx}): {invoice_name}")
            continue

        # البحث في المخزون
        matching_items = old_inventory[
            old_inventory['barcode'].astype(str).str.strip() == invoice_barcode
        ]

        if not matching_items.empty:
            # وُجد تطابق → نحتاج موافقة يدوية
            inventory_name = matching_items.iloc[0]['name']
            matches_requiring_approval.append({
                'index': idx,
                'barcode': invoice_barcode,
                'invoice_name': invoice_name,
                'inventory_name': inventory_name,
                'expiration': str(matching_items.iloc[0].get('expiration', ''))
            })
            result_df.at[idx, 'final_name'] = inventory_name  # الاسم الافتراضي من المخزون
        else:
            # لم نجد تطابق → استخدم اسم الفاتورة مباشرة
            result_df.at[idx, 'final_name'] = invoice_name

    log.info(f"عدد الأصناف التي تحتاج موافقة: {len(matches_requiring_approval)}")

    return result_df, matches_requiring_approval


def resolve_matches_interactively(matches: List[dict]) -> dict:
    """
    عرض التطابقات وطلب موافقة يدوية (interactive mode)

    للكل تطابق:
    - ✓ قبول اسم المخزون
    - ✗ رفض واستخدام اسم الفاتورة
    - ✎ تعديل يدوي

    Args:
        matches: قائمة التطابقات

    Returns:
        dict: {index: final_name}
    """
    resolutions = {}

    for match in matches:
        idx = match['index']
        barcode = match['barcode']
        invoice_name = match['invoice_name']
        inventory_name = match['inventory_name']

        log.info("")
        log.info("=" * 80)
        log.info(f"📌 تطابق #{idx + 1}")
        log.info(f"   الباركود: {barcode}")
        log.info(f"   اسم الفاتورة:    {invoice_name}")
        log.info(f"   اسم المخزون:     {inventory_name}")
        log.info(f"   الصلاحية:        {match.get('expiration', 'N/A')}")

        while True:
            log.info("")
            choice = input(
                "اختر (✓ قبول / ✗ رفض / ✎ تعديل): [1/2/3] "
            ).strip()

            if choice in ['1', '✓']:
                # قبول اسم المخزون
                resolutions[idx] = inventory_name
                log.info(f"✓ تم قبول اسم المخزون")
                break
            elif choice in ['2', '✗']:
                # رفض واستخدام اسم الفاتورة
                resolutions[idx] = invoice_name
                log.info(f"✗ تم استخدام اسم الفاتورة")
                break
            elif choice in ['3', '✎']:
                # تعديل يدوي
                custom_name = input("أدخل الاسم المخصص: ").strip()
                if custom_name:
                    resolutions[idx] = custom_name
                    log.info(f"✎ تم تعديل الاسم إلى: {custom_name}")
                    break
                else:
                    log.warning("الاسم فارغ، حاول مجدداً")
            else:
                log.warning("خيار غير صحيح، اختر 1 أو 2 أو 3")

    log.info("")
    log.info("=" * 80)
    return resolutions


def apply_resolutions(invoice_df: pd.DataFrame, resolutions: dict) -> pd.DataFrame:
    """
    تطبيق قرارات الموافقة على الفاتورة

    Args:
        invoice_df: بيانات الفاتورة المطابقة
        resolutions: {index: final_name}

    Returns:
        الفاتورة بعد تطبيق القرارات
    """
    result_df = invoice_df.copy()

    for idx, final_name in resolutions.items():
        result_df.at[idx, 'final_name'] = final_name

    return result_df
