import os
import pandas as pd
from datetime import datetime
from utils.logger import get_logger

log = get_logger()


class InventoryManager:
    """
    إدارة جرد المخزون التراكمي للمتجر
    """

    def __init__(self, store_id: str):
        self.store_id = store_id
        self.store_path = f"data/{store_id}"
        self.inventory_file = f"{self.store_path}/old_inventory.xlsx"

        # التأكد من وجود مجلد المتجر
        os.makedirs(self.store_path, exist_ok=True)

    def load_old_inventory(self) -> pd.DataFrame:
        """
        قراءة جرد المخزون القديم للمتجر
        """
        if not os.path.exists(self.inventory_file):
            log.info(f"المخزون الأول للمتجر {self.store_id} (لا يوجد مخزون سابق)")
            return pd.DataFrame(columns=['barcode', 'name', 'expiration'])

        try:
            df = pd.read_excel(self.inventory_file)
            log.info(f"تم تحميل المخزون السابق: {len(df)} صنف")
            return df
        except Exception as e:
            log.error(f"خطأ في تحميل المخزون: {e}")
            return pd.DataFrame(columns=['barcode', 'name', 'expiration'])

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
            self.inventory_file = f"{self.store_path}/old_inventory.xlsx"
            updated_inventory.to_excel(self.inventory_file, index=False)
            log.info(f"✓ تم حفظ المخزون المحدث: {self.inventory_file}")
        except Exception as e:
            log.error(f"خطأ في حفظ المخزون: {e}")
