import pyodbc
import pandas as pd
from datetime import datetime

print("=" * 80)
print("🚀 قراءة المنتجات مباشرة من قاعدة البيانات SQL Server")
print("=" * 80)
print()

try:
    # الاتصال بـ SQL Server
    connection_string = (
        'Driver={SQL Server};'
        'Server=localhost;'
        'Database=storedb;'
        'Trusted_Connection=yes;'
    )

    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    print("✅ تم الاتصال بـ SQL Server بنجاح!\n")

    # 1. قراءة قائمة الأصناف (item_list)
    print("📦 قراءة قائمة الأصناف من جدول item_list...")
    cursor.execute("SELECT * FROM item_list")
    items_data = cursor.fetchall()
    items_columns = [desc[0] for desc in cursor.description]

    items_df = pd.DataFrame(items_data, columns=items_columns)
    print(f"   ✓ عدد الأصناف: {len(items_df)}")
    print()

    # 2. قراءة بيانات المخزون (store_file)
    print("📊 قراءة بيانات المخزون من جدول store_file...")
    cursor.execute("SELECT * FROM store_file")
    store_data = cursor.fetchall()
    store_columns = [desc[0] for desc in cursor.description]

    store_df = pd.DataFrame(store_data, columns=store_columns)
    print(f"   ✓ عدد السجلات: {len(store_df)}")
    print()

    # 3. دمج البيانات
    print("🔗 دمج البيانات...")

    # إعادة تسمية الأعمدة للمطابقة
    items_df = items_df.rename(columns={'item_id': 'item_id_items'})

    # الدمج على أساس item_id
    merged_df = store_df.merge(
        items_df[['item_id_items', 'item_name']],
        left_on='item_id',
        right_on='item_id_items',
        how='left'
    )

    # اختيار الأعمدة المهمة
    important_columns = ['item_id', 'item_code', 'item_name', 'qut', 'price2', 'descR']
    available_columns = [col for col in important_columns if col in merged_df.columns]
    final_df = merged_df[available_columns].copy()

    print(f"   ✓ عدد المنتجات المدمجة: {len(final_df)}")
    print()

    # 4. عرض البيانات
    print("=" * 80)
    print("📋 أول 20 منتج:")
    print("=" * 80)
    print(final_df.head(20).to_string())
    print()

    # 5. حفظ في Excel على سطح المكتب
    print("=" * 80)
    filename = f"All_Products_From_Database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"C:\\Users\\naji2\\Desktop\\{filename}"

    final_df.to_excel(filepath, index=False, sheet_name='المنتجات')
    print(f"✅ تم حفظ جميع المنتجات في: {filename}")
    print(f"   📁 الموقع: سطح المكتب")
    print(f"   📊 عدد الصفوف: {len(final_df)}")
    print("=" * 80)

    # 6. إحصائيات سريعة
    print()
    print("📈 إحصائيات سريعة:")
    print(f"   • إجمالي المنتجات: {len(final_df)}")
    print(f"   • الأعمدة: {', '.join(available_columns)}")

    if 'price2' in final_df.columns:
        avg_price = final_df['price2'].mean()
        print(f"   • متوسط السعر: {avg_price:.2f}")

    if 'qut' in final_df.columns:
        total_qty = final_df['qut'].sum()
        print(f"   • إجمالي الكمية: {total_qty:,.0f}")

    print()

    conn.close()

except Exception as e:
    print(f"❌ خطأ: {str(e)}")
    print()
    print("💡 تأكد من:")
    print("   1. تشغيل SQL Server")
    print("   2. تثبيت pyodbc: pip install pyodbc")
    print("   3. وجود الوصول للمصادقة Windows")
