import pandas as pd
from typing import Tuple, List
from rapidfuzz import fuzz
from utils.logger import get_logger

log = get_logger()

FUZZY_MATCH_THRESHOLD = 80  # نسبة التشابه المقبولة


def enrich_invoice_from_supplier(invoice_df: pd.DataFrame, supplier_inventory: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """
    الخطوة الأولى من الطريقة الثانية: إثراء الفاتورة من مخزون المورد

    للكل صنف بالفاتورة:
    1. ابحث عن الاسم في مخزون المورد
    2. احصل على: الباركود + الصلاحية
    3. أضفها للصنف

    Args:
        invoice_df: بيانات الفاتورة
        supplier_inventory: بيانات مخزون المورد

    Returns:
        (enriched_invoice, enrichment_issues)
    """
    enriched = invoice_df.copy()
    enrichment_issues = []

    # إضافة أعمدة جديدة إذا لم تكن موجودة
    if 'barcode' not in enriched.columns:
        enriched['barcode'] = ''
    if 'expiration' not in enriched.columns:
        enriched['expiration'] = ''

    for idx, row in enriched.iterrows():
        invoice_name = str(row.get('name', '')).strip()

        if not invoice_name:
            log.warning(f"صنف بدون اسم (الصف {idx})")
            continue

        # البحث عن الاسم في مخزون المورد (تطابق فازي)
        best_match = None
        best_score = 0

        for _, supplier_row in supplier_inventory.iterrows():
            supplier_name = str(supplier_row['name']).strip()
            score = fuzz.WRatio(invoice_name, supplier_name)

            if score > best_score:
                best_score = score
                best_match = supplier_row

        if best_match is not None and best_score >= FUZZY_MATCH_THRESHOLD:
            # وُجد تطابق
            enriched.at[idx, 'barcode'] = str(best_match['barcode']).strip()
            enriched.at[idx, 'expiration'] = str(best_match['expiration']).strip()
            log.info(f"✓ صنف #{idx}: '{invoice_name}' ← '{best_match['name']}' (تطابق: {best_score}%)")
        else:
            # لم نجد تطابق → صنف جديد
            enrichment_issues.append({
                'index': idx,
                'name': invoice_name,
                'reason': 'no_match' if not best_match else f'low_score_{best_score}'
            })
            log.warning(f"✗ صنف جديد #{idx}: '{invoice_name}' (لم نجد تطابق)")

    log.info(f"تم إثراء الفاتورة: {enriched['barcode'].notna().sum()} صنف مع بيانات")
    return enriched, enrichment_issues


def match_enriched_invoice_with_inventory(enriched_invoice: pd.DataFrame, old_inventory: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """
    الخطوة الثانية من الطريقة الثانية: مطابقة الفاتورة المُثرية مع مخزون المتجر

    للكل صنف (الآن مع باركود + صلاحية):
    1. ابحث عن الباركود في مخزون المتجر
    2. إذا موجود → احصل على الاسم (من المتجر)
    3. إذا لم يوجد → صنف جديد، استخدم اسم الفاتورة

    Args:
        enriched_invoice: الفاتورة بعد الإثراء
        old_inventory: مخزون المتجر

    Returns:
        (df_with_matched_names, matches_needing_approval)
    """
    result_df = enriched_invoice.copy()
    matches_requiring_approval = []

    if 'final_name' not in result_df.columns:
        result_df['final_name'] = result_df.get('name', '')

    for idx, row in result_df.iterrows():
        barcode = str(row.get('barcode', '')).strip()
        invoice_name = str(row.get('name', '')).strip()
        expiration = str(row.get('expiration', '')).strip()

        if not barcode:
            # صنف بدون باركود (لم يتم إثراؤه من المورد) → استخدم اسم الفاتورة
            result_df.at[idx, 'final_name'] = invoice_name
            continue

        # البحث في مخزون المتجر
        matching_items = old_inventory[
            old_inventory['barcode'].astype(str).str.strip() == barcode
        ]

        if not matching_items.empty:
            # وُجد تطابق → نحتاج موافقة يدوية على الاسم
            inventory_name = matching_items.iloc[0]['name']
            matches_requiring_approval.append({
                'index': idx,
                'barcode': barcode,
                'invoice_name': invoice_name,
                'inventory_name': inventory_name,
                'expiration': expiration
            })
            result_df.at[idx, 'final_name'] = inventory_name  # الاسم الافتراضي من المخزون
        else:
            # صنف جديد (موجود في المورد لكن ليس في المتجر)
            result_df.at[idx, 'final_name'] = invoice_name

    log.info(f"عدد الأصناف التي تحتاج موافقة: {len(matches_requiring_approval)}")
    return result_df, matches_requiring_approval


def resolve_method2_matches_interactively(matches: List[dict]) -> dict:
    """
    عرض التطابقات في الطريقة الثانية وطلب موافقة يدوية

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
                "اختر (✓ قبول اسم المخزون / ✗ استخدام اسم الفاتورة / ✎ تعديل): [1/2/3] "
            ).strip()

            if choice in ['1', '✓']:
                resolutions[idx] = inventory_name
                log.info(f"✓ تم قبول اسم المخزون")
                break
            elif choice in ['2', '✗']:
                resolutions[idx] = invoice_name
                log.info(f"✗ تم استخدام اسم الفاتورة")
                break
            elif choice in ['3', '✎']:
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
