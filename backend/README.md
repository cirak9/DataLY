# DataLY Backend (FastAPI)

يعيد استخدام منطق العمل الحقيقي من الأداة الأصلية (`extractors/`, `transformers/`,
`fusion/`, `utils/`, `adapters/` بجذر المشروع) فوق قاعدة بيانات PostgreSQL بدل ملفات
إكسل. خط الأنابيب كامل ومتحقق منه فعلياً ضد Supabase حقيقية — راجع `docs/REBUILD_PLAN.md`
للخطة الكاملة وقرارات التصميم.

**منشور فعلياً على Render:** https://dataly-backend.onrender.com (`/docs` لتوثيق
Swagger التفاعلي). الاستضافة المجانية تنام بعد فترة خمول — أول طلب بعدها يأخذ 30-50 ثانية.

## النشر (Render + Supabase)

متغيرات البيئة المطلوبة على Render (لوحة تحكم الخدمة → Environment):

```
DATABASE_URL=postgresql+psycopg2://...   # من Supabase، لازم +psycopg2 يدوياً (Supabase يعطيها بدونها)
JWT_SECRET=<سلسلة عشوائية طويلة>
CORS_ORIGINS=["https://<رابط-الواجهة-على-Vercel>"]
```

**قرار تصميم مهم — التنزيل يُعاد بناؤه من قاعدة البيانات، مو من القرص:** قرص Render
المجاني مؤقت (ينمسح بإعادة النشر/إعادة التشغيل). في البداية كان `GET
/invoices/{id}/export/download` يقرأ ملف `.xlsx` محفوظ على القرص وقت التصدير — لما
القرص انمسح بعد إعادة نشر، صار `FileResponse` يفشل باستثناء غير معالَج قبل أي استجابة،
والاستثناء يهرب من `CORSMiddleware` فيوصل للمتصفح كـ"CORS policy" مضلِّل بدل الخطأ
الحقيقي (500). الحل: `export_service.build_export_bytes()` يبني الملف من بيانات
الفاتورة بقاعدة البيانات مباشرة بكل تنزيل، بدل الاعتماد على وجود ملف فعلي على القرص —
`export_invoice()` لسا يكتب نسخة على القرص كأرشيف، بس التنزيل ما يعتمد عليها.

## الإعداد المحلي

1. **قاعدة بيانات Postgres** — أي وحدة من الاثنين:
   - محلياً عبر Docker: `docker compose up -d` (بجذر المشروع، يشغّل Postgres على `localhost:5432`).
   - أو حساب Supabase مجاني (نفس الخدمة المستخدمة بالاستضافة) — أنشئ مشروع، وخذ الـ`DATABASE_URL` من إعدادات الاتصال.

2. **بيئة بايثون:**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env   # وعبّي DATABASE_URL/JWT_SECRET
   ```

3. **تشغيل الهجرات (إنشاء الجداول + بذر التصنيفات):**
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
  models/      SQLAlchemy — كل الجداول (users, stores, invoices, sessions, ...)
  schemas/     Pydantic (شكل الطلبات/الردود)
  api/routes/  نقاط الـAPI — راجع القائمة الكاملة تحت
  services/    منطق تنسيق العمليات (DB + orchestration)
  core_logic/  منطق العمل المنقول من الأداة الأصلية — دوال نصية بحتة، بلا أي DB،
               قابلة للاختبار بمعزل (base_cleaner, categorizer, reconciliation,
               invoice_calc, alsahl_export, excel_extractor, validators)
alembic/       هجرات قاعدة البيانات (تشمل هجرة بيانات تبذر 32 تصنيف/165 كلمة مفتاحية)
```

الفصل المتعمَّد بين `core_logic/` و`services/`: كل ملف بـ`core_logic/` دالة نصية/حسابية
بحتة (نص أو DataFrame في المدخل، نص أو رقم بالمخرج) بدون أي اتصال قاعدة بيانات — نفس
منطق الأداة الأصلية حرفياً أو شبه حرفي. `services/` هي طبقة التنسيق اللي تقرأ/تكتب
DB وتستدعي `core_logic/` — بهذا منطق العمل يبقى قابل للاختبار بمعزل عن أي DB حقيقية.

## خط أنابيب الفاتورة — نقاط الـAPI

كل نقطة محمية بتوكن JWT (`Authorization: Bearer <token>`) إلا `/auth/login`.

```
POST   /auth/login                                     تسجيل دخول → JWT
GET    /auth/me                                         بيانات المستخدم الحالي

GET/POST  /stores                                       المتاجر
GET/POST  /suppliers                                     الموردون

POST   /stores/{store_id}/invoices                       رفع فاتورة (xlsx/xls)
GET    /stores/{store_id}/invoices                        فواتير المتجر
GET    /invoices/{id}                                      بيانات فاتورة واحدة
POST   /invoices/{id}/clean                                 تنظيف + تصنيف تلقائي → invoice_items
GET    /invoices/{id}/items                                  أصناف الفاتورة
PATCH  /invoices/{id}/items/{item_id}                          تعديل صنف يدوياً

POST   /invoices/{id}/session                                   إنشاء جلسة استلام
GET    /sessions/{id}                                             حالة الجلسة + الأصناف
PATCH  /sessions/{id}/items/{item_id}                               تعبئة باركود/صلاحية/سعر
POST   /sessions/{id}/complete                                       إكمال + تفعيل التسوية تلقائياً

GET    /invoices/{id}/reconciliation-matches                          تطابقات التسوية
POST   /reconciliation-matches/{id}/decide                              قرار: approve|reject|manual

POST   /invoices/{id}/merge                                               دمج بالمخزون + تعلّم الفهرس المشترك

POST   /invoices/{id}/export                                               توليد ملف Alsahl (أرشيف كامل)
GET    /invoices/{id}/export/download                                      تنزيل آخر تصدير
```

**دورة حياة الفاتورة (`Invoice.status`):**
`uploaded → cleaned → session_pending → session_complete → reconciled → merged → exported`

كل انتقال يصير بفعل صريح (نقطة API واحدة)، ولا مرحلة تُتخطى — نقطة التسوية والدمج
والتصدير كلها ترفض 422 لو الفاتورة لسا ما وصلت المرحلة المطلوبة.

## قرارات تصميم محفوظة من الأداة الأصلية

- **الباركود هو مرساة الهوية** بالتسوية — الاسم يتغير بصيغ كثيرة حسب المورد، الباركود لأ.
- **ولا تطابق تسوية يُطبَّق تلقائياً**، مهما كانت نسبة التشابه — دايماً بانتظار قرار بشري
  صريح (`approve`/`reject`/`manual`) عبر `POST /reconciliation-matches/{id}/decide`.
- **`per_box` (عدد القطع بالعبوة) يبقى `NULL` صراحة لو غير معروف من الفاتورة** — أبداً
  قيمة افتراضية 1 ملفّقة توهم إنها بيانات حقيقية (بق حقيقي انصلح بالأداة الأصلية).
- **`product_catalog` فهرس مشترك بين كل المتاجر**، يتراكم تلقائياً من كل فاتورة تُدمج —
  لكن التسمية الأولى بس تتراكم بلا شرط؛ إعادة تسمية باركود موجود أصلاً لازم تمر عبر
  التسوية (موافقة بشرية)، أبداً استبدال صامت.
- **`inventory_lots` فريد بـ(متجر، باركود، صلاحية)** — نفس صنف بصلاحيات مختلفة (دفعات
  وصول مختلفة) يبقى صفوف منفصلة عمداً؛ upsert بقاعدة "آخر فاتورة تحل محل بيانات نفس
  اللوت بالكامل" (`ON CONFLICT ... DO UPDATE`).
- **`stores.owner_id` هو حد العزل بين العملاء** — كل متجر مملوك لمستخدم واحد، وكل نقطة
  API متفرعة من `store_id` (فواتير، جلسات، تسويات، مخزون، تصدير) تتحقق من الملكية عبر
  دوال `get_owned_*` بـ`app/api/deps.py` قبل أي قراءة أو تعديل — 404 لا 403 لو المتجر
  موجود بس مملوك لمستخدم ثاني، عشان ما نسرّب حتى معلومة وجوده. `product_catalog`
  والتصنيفات والموردون يبقون مشتركين عمداً بين كل العملاء (فهرس/تصنيف عام، مو بيانات
  تجارية حساسة) — العزل يشمل بس البيانات الخاصة بكل متجر.
