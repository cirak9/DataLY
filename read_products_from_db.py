import pyodbc
import pandas as pd
from datetime import datetime

# الاتصال بـ SQL Server مباشرة
try:
    # محاولة الاتصال
    connection_string = (
        'Driver={SQL Server};'
        'Server=localhost;'
        'Database=storedb;'
        'Trusted_Connection=yes;'
    )

    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    print("=" * 70)
    print("✅ تم الاتصال بـ SQL Server بنجاح!")
    print("=" * 70)
    print()

    # استعلام لقراءة الجداول المتاحة
    print("📊 الجداول المتاحة في قاعدة البيانات:")
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE='BASE TABLE'
    """)

    tables = cursor.fetchall()
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table[0]}")

    print()
    print("=" * 70)

    # البحث عن جدول المنتجات
    product_tables = ['products', 'items', 'Products', 'Items', 'منتجات', 'أصناف']

    for table_name in product_tables:
        try:
            cursor.execute(f"SELECT TOP 5 * FROM {table_name}")
            columns = [desc[0] for desc in cursor.description]
            print(f"✅ وجدت جدول المنتجات: {table_name}")
            print(f"   الأعمدة: {', '.join(columns)}")
            print()

            # قراءة جميع المنتجات
            cursor.execute(f"SELECT * FROM {table_name}")
            products = cursor.fetchall()

            print(f"📈 عدد المنتجات: {len(products)}")
            print()

            # إنشاء DataFrame
            df = pd.DataFrame([tuple(p) for p in products], columns=columns)

            # عرض أول 10 منتجات
            print("أول 10 منتجات:")
            print(df.head(10).to_string())
            print()

            # حفظ في Excel
            filename = f"products_from_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = f"C:\\Users\\naji2\\Desktop\\{filename}"
            df.to_excel(filepath, index=False)
            print(f"✅ تم حفظ المنتجات في: {filepath}")

            break
        except:
            continue

    conn.close()

except Exception as e:
    print(f"❌ خطأ في الاتصال: {str(e)}")
    print()
    print("💡 الحلول:")
    print("1. تأكد من تشغيل SQL Server")
    print("2. قد تحتاج لتثبيت: pip install pyodbc")
    print("3. قد تحتاج للمصادقة بكلمة مرور بدلاً من Trusted_Connection")
