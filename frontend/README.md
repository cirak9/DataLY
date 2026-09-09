# DataLY Frontend (React + Vite + TypeScript)

**منشورة فعلياً على Vercel:** https://data-ly.vercel.app

## المتطلبات

- **Node.js** نسخة 18 أو أحدث.

## الإعداد المحلي

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL يشاور على backend المحلي (http://localhost:8000)
npm run dev
```

يفتح على http://localhost:5173 — لازم الـbackend شغّال بنفس الوقت (راجع `backend/README.md`).

## النشر (Vercel)

متغير بيئة واحد مطلوب على Vercel: `VITE_API_URL` = رابط الباك إند على Render.

`vercel.json` يحتوي rewrite إجباري (`/(.*) → /index.html`) — بدونه أي دخول مباشر
(تحديث صفحة، رابط مُرسَل) لمسار متداخل زي `/stores/3/history` يرجع 404 من Vercel، لأنه
بحث عن ملف فعلي بهذا المسار بدل ما يسلّم `index.html` لـ React Router يتولى التوجيه.

## بنية المجلد

```
src/
  lib/         عميل API (axios)، سياق تسجيل الدخول (auth context)
  components/  عناصر واجهة مشتركة
  pages/       شاشة لكل route — راجع App.tsx للقائمة الكاملة
```

## الشاشات

كل الشاشات مبنية فعلياً ومتصلة بالباك إند الحقيقي، ومتحقَّق منها حياً على سطح مكتب،
تابلت، وموبايل:

```
/login                                تسجيل الدخول
/stores                                قائمة المتاجر
/stores/:id/invoices                    فواتير المتجر + رفع فاتورة جديدة
/invoices/:id/review                      مراجعة الأصناف بعد التنظيف التلقائي
/invoices/:id/session                      جلسة استلام التاجر (باركود/صلاحية/سعر)
/invoices/:id/reconciliation                 تسوية الأصناف (قبول/رفض/تسمية يدوية)
/invoices/:id/export                          الدمج بالمخزون + تصدير ملف Alsahl
/stores/:id/inventory                    مخزون المتجر التراكمي
/stores/:id/history                       سجل الفواتير المصدَّرة + إعادة تنزيل
```

**تصميم متجاوب:** كل شاشة فيها جدول تعرض جدولاً كاملاً من `sm:` فما فوق (تابلت/سطح
مكتب)، وقائمة بطاقات عمودية تحت `sm:` (موبايل) — بدل تمرير أفقي مزعج لجدول بعرض شاشة
حاسوب على شاشة هاتف. شاشة الجلسة تستخدم تخطيط عمودين (قائمة جانبية + بطاقة الصنف
النشط) من `md:` فما فوق.
