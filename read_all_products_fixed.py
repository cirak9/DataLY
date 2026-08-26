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

    # قراءة المنتجات بشكل مباشر
    print("📊 قراءة بيانات المخزون من جدول store_file...")
    query = """
    SELECT TOP 10000
        item_id,
        item_code,
        qut as quantity,
        price2 as price,
        descR as description
    FROM store_file
    WHERE item_code IS NOT NULL AND item_code != ''
    """

    df = pd.read_sql(query, conn)

    print(f"   ✓ عدد المنتجات المقروءة: {len(df)}")
    print()

    # عرض البيانات
    print("=" * 80)
    print("📋 أول 30 منتج:")
    print("=" * 80)
    print(df.head(30).to_string())
    print()

    # حفظ في Excel
    print("=" * 80)
    filename = f"Products_From_EasySoft_Database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"C:\\Users\\naji2\\Desktop\\{filename}"

    df.to_excel(filepath, index=False, sheet_name='Products')
    print(f"✅ تم حفظ جميع المنتجات!")
    print(f"   📁 الملف: {filename}")
    print(f"   📊 عدد الصفوف: {len(df)}")
    print("=" * 80)

    # إحصائيات
    print()
    print("📈 إحصائيات سريعة:")
    print(f"   • إجمالي المنتجات: {len(df)}")
    if 'price' in df.columns:
        print(f"   • متوسط السعر: {df['price'].mean():.2f}")
    if 'quantity' in df.columns:
        print(f"   • إجمالي الكمية: {df['quantity'].sum():,.0f}")
    print()

    conn.close()

except Exception as e:
    print(f"❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()
