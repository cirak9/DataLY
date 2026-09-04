import os
import pandas as pd
from datetime import datetime
from utils.logger import get_logger

log = get_logger()


class InventoryLoadError(Exception):
    """يُرفع لو old_inventory.xlsx موجود فعلاً لكن فشلت قراءته (مقفول ببرنامج آخر، تالف...).
    مقصود عدم ابتلاعه بصمت: update_inventory() يتعامل مع "مخزون فاضٍ" على إنه "أول مخزون
    للمتجر" ويستبدل كل شي بالفاتورة الجديدة — فخطأ قراءة حقيقي، لو ابتلع بصمت، يمسح كل
    تاريخ المخزون الفعلي بدون أي تحذير واضح للمستخدم (حصل فعليًا — راجع الكوميت)."""
    pass


class InventoryManager:
    """
    إدارة جرد المخزون التراكمي للمتجر
    """

    def __init__(self, store_id: str = ""):
        # store_id فاضٍ = العمل مباشرة بجذر data/ بدون مجلد متجر — لدعم تشغيل يدوي بسيط
        # (متجر واحد بالمرة، بدون --store) قبل ما يستاهل الاستثمار بهيكلية متعددة المتاجر.
        self.store_id = store_id
        self.store_path = os.path.join("data", store_id) if store_id else "data"
        self.inventory_file = os.path.join(self.store_path, "old_inventory.xlsx")

        # التأكد من وجود المجلد
        os.makedirs(self.store_path, exist_ok=True)

    def load_old_inventory(self) -> pd.DataFrame:
        """
        قراءة جرد المخزون القديم للمتجر — عبر نفس كشف الأعمدة الذكي اللي extract_old_inventory()
        يستخدمه (extractors/inventory_extractor.py)، مو قراءة خام تفترض أعمدة barcode/name/
        expiration جاهزة بالضبط بالملف. مهم: old_inventory.xlsx ممكن يكون ملف خام حقيقي
        (تصدير من نظام نقاط بيع، بأعمدة زي cc/descR/date_xp) وضعه المستخدم مباشرة — قراءة
        خام بدون كشف كانت تفشل بصمت تام: reconcile() يقارن الباركود بعمود "barcode" حرفياً،
        فلو الملف ما فيه عمود بهذا الاسم، كل مطابقة تفشل بصمت بدون أي خطأ ظاهر (حصل فعليًا).
        """
        if not os.path.exists(self.inventory_file):
            log.info(f"المخزون الأول للمتجر {self.store_id or '(data/ مباشرة)'} (لا يوجد مخزون سابق)")
            return pd.DataFrame(columns=['barcode', 'name', 'expiration'])

        from extractors.inventory_extractor import extract_old_inventory
        try:
            df = extract_old_inventory(self.inventory_file, store_id=self.store_id)
            log.info(f"تم تحميل المخزون السابق: {len(df)} صنف")
            return df
        except Exception as e:
            # فشل قراءة ملف موجود فعلاً — نوقف بوضوح بدل الاستمرار بمخزون فاضٍ (يُفهم لاحقاً
            # كـ"أول مخزون للمتجر" ويمسح كل التاريخ الحقيقي بصمت عند update_inventory()).
            raise InventoryLoadError(
                f"فشلت قراءة {self.inventory_file} رغم وجوده — لن نكمل بافتراض مخزون فاضٍ "
                f"(قد يمسح كل تاريخ المخزون الحقيقي لهذا المتجر). تأكد إن الملف مو مفتوح ببرنامج "
                f"آخر (إكسل مثلاً) وصيغته سليمة، وحاول من جديد. الخطأ الأصلي: {e}"
            ) from e

    def update_inventory(self, old_inventory: pd.DataFrame, processed_invoice: pd.DataFrame) -> pd.DataFrame:
        """
        تحديث المخزون بإضافة كمية الفاتورة الجديدة

        Args:
            old_inventory: المخزون القديم
            processed_invoice: الفاتورة المعالجة (مع الموافقات)

        Returns:
            المخزون المحدث
        """

        # إذا لم يكن هناك مخزون قديم، نبدأ من الفاتورة
        if old_inventory.empty:
            log.info("إضافة الفاتورة كمخزون ابتدائي")
            return processed_invoice[['barcode', 'name', 'expiration']].copy()

        # الأعمدة المطلوبة من الفاتورة
        if not all(col in processed_invoice.columns for col in ['barcode', 'name', 'expiration']):
            log.warning("الأعمدة المطلوبة غير موجودة في الفاتورة المعالجة")
            return old_inventory

        # دمج المخزون القديم مع الفاتورة الجديدة
        # نضيف فقط الأصناف الجديدة من الفاتورة
        new_items = processed_invoice[['barcode', 'name', 'expiration']].copy()

        # ربط المخزون القديم مع الأصناف الجديدة
        updated = pd.concat([old_inventory, new_items], ignore_index=True)

        # إزالة التكرارات (نفس الباركود + الصلاحية = نفس الصنف)
        # نبقي على آخر إدخال (الأحدث)
        updated = updated.drop_duplicates(subset=['barcode', 'expiration'], keep='last')

        log.info(f"تم تحديث المخزون: {len(updated)} صنف نهائي")
        return updated.reset_index(drop=True)

    def save_updated_inventory(self, updated_inventory: pd.DataFrame):
        """
        حفظ المخزون المحدث

        هذا الحفظ **للفائدة المستقبلية فقط**
        لا علاقة بالملف الذي يُصدّر للمنظومة
        """
        if updated_inventory.empty:
            log.warning("المخزون فارغ، لا يتم الحفظ")
            return

        try:
            updated_inventory.to_excel(self.inventory_file, index=False)
            log.info(f"✓ تم حفظ المخزون المحدث: {self.inventory_file}")
        except Exception as e:
            log.error(f"خطأ في حفظ المخزون: {e}")
