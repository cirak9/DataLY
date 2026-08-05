# DataLY v6.0.0

نظام معالجة فواتير الموردين وتصديرها لمنظومة السهل — للسوق الليبي.

## التشغيل السريع

```bash
pip install -r requirements.txt

# 1) معالجة فاتورة جديدة
python main.py invoice.xlsx

# 2) أرسل data/session_template.xlsx للتاجر، أو شغّل واجهة الاستلام:
streamlit run session/receiving_app.py

# 3) بعد ما يخلّص التاجر، انقل session_output.xlsx لمجلد data/

# 4) ادمج وصدّر لملف السهل
python main.py --merge
```

الناتج النهائي: `output/output_alsahl.xlsx` — ارفعه في شاشة "فاتورة مشتريات" بمنظومة السهل.

## تشغيل الاختبارات

```bash
pytest tests/ -v
```

## هيكل المشروع

```
DataLY/
├── extractors/       ← قراءة إكسل الفاتورة الخام
├── transformers/      ← تنظيف وتحقق من صحة البيانات
├── session/            ← توليد جلسة استلام التاجر (Streamlit)
├── fusion/              ← دمج بيانات الفاتورة مع جلسة التاجر
├── adapters/             ← تصدير لصيغة منظومة السهل
├── utils/                 ← تصنيف الأصناف + تحقق + تسجيل (logging)
├── tests/                  ← اختبارات pytest
├── data/                    ← ملفات العمل (تلقائي، فيه نسخ احتياطية بـ data/backups/)
├── output/                   ← الملف النهائي لمنظومة السهل
└── logs/                       ← سجل كامل لكل تشغيلة (dataly.log)
```

## ملاحظات مهمة

- **`utils/categories.json`** هو المصدر الوحيد لتصنيفات الأصناف (أسماء + كلمات مفتاحية). نفس الملف موجود بمشروع `DataLY_OCR` المستقل — راجع `sync_categories.py` هناك لو عدّلت تصنيف.
- **الكمية بالفاتورة تُفهم كعدد قطع مفردة** (مؤكد من صاحب المشروع)، وعمود "الصندوق" رقم مرجعي كسري مقصود، مو خطأ.
- كل تشغيلة تُسجَّل كاملة بـ `logs/dataly.log` — راجعه أول شي لو صار خطأ غامض.
- `data/backups/` يحتفظ بنسخة من `invoice_data.xlsx` و`session_output.xlsx` قبل كل عملية دمج.

## للمزيد

راجع `ARCHITECTURE.md` لقرارات التصميم و`CHANGELOG.md` لتاريخ الإصدارات.
