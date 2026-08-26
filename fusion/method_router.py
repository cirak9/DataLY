import os
from utils.logger import get_logger

log = get_logger()


def detect_method(supplier_inventory_path: str = None, method_override: int = None) -> int:
    """
    تحديد الطريقة (1 أو 2) تلقائياً أو يدويًا

    Args:
        supplier_inventory_path: مسار مخزون المورد (اختياري)
        method_override: فرض طريقة معينة (1 أو 2)

    Returns:
        1 للطريقة الأولى، 2 للطريقة الثانية
    """

    # إذا تم تحديد الطريقة يدويًا
    if method_override:
        if method_override not in [1, 2]:
            raise ValueError("الطريقة يجب أن تكون 1 أو 2")
        log.info(f"استخدام الطريقة {method_override} (محددة يدويًا)")
        return method_override

    # الكشف التلقائي
    if supplier_inventory_path and os.path.exists(supplier_inventory_path):
        log.info("مخزون المورد موجود → استخدام الطريقة الثانية")
        return 2
    else:
        log.info("مخزون المورد غير موجود → استخدام الطريقة الأولى")
        return 1
