import pyodbc
import pandas as pd

try:
    connection_string = (
        'Driver={SQL Server};'
        'Server=localhost;'
        'Database=storedb;'
        'Trusted_Connection=yes;'
    )

    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # الجداول المحتملة للمنتجات
    candidate_tables = ['item_list', 'Gfile', 'sall_file', 'itemscode', 'InvFile', 'store_file', 'Dfile']

    print("🔍 البحث عن جدول المنتجات...\n")

    for table_name in candidate_tables:
        try:
            cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
            columns = [desc[0] for desc in cursor.description]
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"✅ جدول: {table_name}")
                print(f"   عدد الصفوف: {count}")
                print(f"   الأعمدة: {', '.join(columns[:10])}")  # أول 10 أعمدة
                print()

                # اذا كان هذا جدول المنتجات، اقرأه
                if 'name' in [c.lower() for c in columns] or 'product' in [c.lower() for c in columns]:
                    print(f"   ✨ هذا قد يكون جدول المنتجات!")
                    cursor.execute(f"SELECT TOP 5 * FROM [{table_name}]")
                    sample = cursor.fetchall()
                    df = pd.DataFrame(sample, columns=columns)
                    print(df.to_string())
                    print()

        except Exception as e:
            pass

    conn.close()
    print("=" * 70)

except Exception as e:
    print(f"❌ خطأ: {str(e)}")
