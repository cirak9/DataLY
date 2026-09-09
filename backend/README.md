# DataLY Backend (FastAPI)

Backend الجديد يعيد استخدام منطق العمل الحقيقي من الأداة الأصلية (`extractors/`,
`transformers/`, `fusion/`, `utils/`, `adapters/` بجذر المشروع) فوق قاعدة بيانات
PostgreSQL بدل ملفات إكسل. راجع الخطة الكاملة بـ[`docs/REBUILD_PLAN.md`](../docs/REBUILD_PLAN.md).

## الإعداد المحلي

1. **قاعدة بيانات Postgres** — أي وحدة من الاثنين:
   - محلياً عبر Docker: `docker compose up -d` (بجذر المشروع، يشغّل Postgres على `localhost:5432`).
   - أو حساب Supabase مجاني (نفس الخدمة اللي راح نستخدمها بالاستضافة لاحقاً) — أنشئ مشروع، وخذ الـ`DATABASE_URL` من إعدادات الاتصال.

2. **بيئة بايثون:**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env   # وعبّي DATABASE_URL/JWT_SECRET
   ```

3. **تشغيل الهجرات (إنشاء الجداول):**
   ```bash
   python -m alembic upgrade head
   ```

4. **إنشاء المستخدم الإداري الوحيد:**
   ```bash
   python scripts/create_admin.py you@example.com "كلمة-مرور-قوية"
   ```

5. **تشغيل السيرفر:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   وثائق تفاعلية (Swagger): http://localhost:8000/docs

## الاختبارات

```bash
pytest
```

## بنية المجلد

```
app/
  core/        إعدادات، اتصال قاعدة البيانات، JWT
  models/      SQLAlchemy — نفس الجداول بخطة إعادة البناء
  schemas/     Pydantic (شكل الطلبات/الردود)
  api/routes/  نقاط الـAPI
  services/    منطق تنسيق العمليات (هيُبنى بالمرحلة 1)
  core_logic/  منطق العمل المنقول من الأداة الأصلية (هيُبنى بالمرحلة 1)
alembic/       هجرات قاعدة البيانات
```
