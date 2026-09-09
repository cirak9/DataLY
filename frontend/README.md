# DataLY Frontend (React + Vite + TypeScript)

## المتطلبات

- **Node.js** (نسخة 18 أو أحدث) — غير مثبّت على هذا الجهاز حالياً. حمّله من
  [nodejs.org](https://nodejs.org) (النسخة LTS) قبل أي شي.

## الإعداد المحلي

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL يشاور على backend المحلي (http://localhost:8000)
npm run dev
```

يفتح على http://localhost:5173 — لازم الـbackend شغّال بنفس الوقت (راجع `backend/README.md`).

## بنية المجلد

```
src/
  lib/         عميل API (axios)، سياق تسجيل الدخول (auth context)
  components/  عناصر واجهة مشتركة
  pages/       شاشة لكل route — راجع App.tsx للقائمة الكاملة
```

معظم الشاشات حالياً حواجز مكان مؤقتة (`ComingSoon`) — تُبنى فعلياً بالمرحلة 2 من
[خطة إعادة البناء](../docs/REBUILD_PLAN.md). `Login` و`Stores` مبنيّتين فعلياً
ومتصلتين بالـbackend الحقيقي كإثبات إن كامل السلسلة (React → FastAPI → Postgres) شغّالة.
