# CHANGELOG.md

## v6.1.0 — النسخة الحالية
- 🆕 `fusion/reconciliation.py` — خطوة توحيد الأصناف عبر الباركود مقابل `data/master_items.xlsx`
  (يُنشأ تلقائيًا)، بمطابقة تقريبية (rapidfuzz) كخط دفاع احتياطي عند غياب الباركود، وملف
  `data/reconciliation_review.xlsx` لأي تعارض حقيقي يحتاج مراجعة بشرية بدل دمج أعمى.
- 🆕 `python main.py --merge` يشغّل التوحيد تلقائيًا قبل الدمج والتصدير.
- 🆕 نسخة احتياطية لـ `master_items.xlsx` قبل كل عملية دمج (بنفس فلسفة invoice_data/session_output).
- 🆕 مجلد tests/ — اختبارات `test_reconciliation.py` (7 اختبارات جديدة).
- 🧹 تنظيف توثيق: إزالة إشارات `DataLY_OCR` و Tesseract من ARCHITECTURE.md/README.md بعد حذف
  ذاك المشروع فعليًا (OCR مؤجَّل عمدًا، بدون تأثير على هذا المشروع).

## v6.0.0
- 🔴 إصلاح: عمود "تكلفة الوحدة" كان يتصفّر بعد الدمج (تعارض اسم عمود بين invoice_data وsession_output)
- 🟠 إصلاح: تطبيق نسبة الخصم على حسابات التكلفة (كانت متجاهَلة تماماً)
- 🟡 إصلاح: كود الصنف من المورد يُستخدم كـ fallback لو ما فيه باركود من التاجر
- 🆕 categories.json كمصدر وحيد للتصنيفات (بدل تكرارها بالكود) + إصلاح خلل "صن" داخل "صنف"
- 🆕 utils/validators.py — توقف واضح لو أعمدة أساسية مفقودة أو بيانات سالبة
- 🆕 utils/logger.py — تسجيل كامل لكل تشغيلة بـ logs/dataly.log
- 🆕 نسخ احتياطية تلقائية لـ invoice_data.xlsx وsession_output.xlsx قبل كل دمج (data/backups/)
- 🆕 مجلد tests/ باختبارات pytest (11 اختبار)
- 🆕 ترقيم إصدار صريح (VERSION، ARCHITECTURE.md، هذا الملف)

## v5 وما قبلها
- النسخة الأصلية بدون الإصلاحات أعلاه — راجع محادثات التطوير للتفاصيل.
