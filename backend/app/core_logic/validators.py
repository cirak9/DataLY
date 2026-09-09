# منقول حرفياً من utils/validators.py بالأداة الأصلية — صفر تغيير بالمنطق، راجع
# docs/REBUILD_PLAN.md قسم 2. رسائل الخطأ هنا (عربية، جاهزة للمستخدم أصلاً) تصير هي
# نفسها جسم رد HTTP 422 بالـAPI — لا داعي لإعادة صياغتها.
from app.core_logic._logger import get_logger

log = get_logger()

REQUIRED_AFTER_RENAME = ["item_name"]
RECOMMENDED_AFTER_RENAME = ["boxes", "cost_price"]


class InvoiceValidationError(Exception):
    """يُرفع لما الفاتورة المستخرجة ناقصة أعمدة أساسية لا يمكن الاستمرار بدونها."""
    pass


def validate_extracted_columns(df) -> None:
    missing_required = [c for c in REQUIRED_AFTER_RENAME if c not in df.columns]
    if missing_required:
        raise InvoiceValidationError(
            "تعذّر إيجاد عمود 'اسم الصنف' بالفاتورة. "
            "تأكد إن رأس الجدول بالإكسل يحتوي أحد هذي الأسماء: "
            "'اسم الصنف' / 'اسم المنتج' / 'البيان' / 'الوصف'. "
            "لو اسم العمود عندك مختلف، أضفه لقائمة POSSIBLE_COLUMNS['item_name'] "
            "بملف app/core_logic/excel_extractor.py."
        )

    missing_recommended = [c for c in RECOMMENDED_AFTER_RENAME if c not in df.columns]
    if missing_recommended:
        log.warning(
            f"[تحذير] لم يتم إيجاد الأعمدة: {missing_recommended} — "
            "سيتم المتابعة بقيم صفرية لهذي الحقول، لكن راجع النتيجة النهائية بعناية."
        )


def validate_clean_dataframe(df) -> None:
    if df.empty:
        raise InvoiceValidationError(
            "بعد التنظيف، لم يتبقَ أي صنف صالح. "
            "تحقق من ملف الفاتورة — ربما كل الصفوف اتصنّفت كملاحظات أو إجماليات بالخطأ."
        )

    if "boxes" in df.columns:
        try:
            if (df["boxes"] < 0).any():
                bad_rows = df[df["boxes"] < 0]["item_name"].tolist()
                raise InvoiceValidationError(
                    f"وُجدت كمية سالبة بالأصناف التالية: {bad_rows} — راجع الفاتورة الأصلية."
                )
        except (TypeError, ValueError):
            pass

    for price_col in ("cost_price", "total_price"):
        if price_col in df.columns:
            try:
                if (df[price_col] < 0).any():
                    bad_rows = df[df[price_col] < 0]["item_name"].tolist()
                    raise InvoiceValidationError(
                        f"وُجد سعر سالب ({price_col}) بالأصناف التالية: {bad_rows} — راجع الفاتورة الأصلية."
                    )
            except (TypeError, ValueError):
                pass

    log.info(f"[تحقق] {len(df)} صنف اجتاز التحقق بنجاح")
