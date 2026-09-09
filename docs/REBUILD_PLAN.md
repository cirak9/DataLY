# DataLY → Web App Rebuild

> **حالة التنفيذ:** المرحلة 0 (السقالة) خلصت **ومتحقق منها فعلياً ضد قاعدة بيانات حقيقية**
> — المستخدم أنشأ حساب ومشروع Supabase (مشروع "dataly"، منطقة أوروبا)، وشُغّلت الهجرة
> فعلياً: 13 جدول + `alembic_version` موجودين بالفعل بقاعدة البيانات، وتحقّقت الحالتان
> الحرجتان مباشرة من `information_schema`/`pg_indexes` (عمود `box_count` محسوب فعلياً،
> فهرس `ux_inventory_lot` بالـCOALESCE موجود وشغّال). سلسلة كاملة (تسجيل دخول → JWT →
> إنشاء متجر باسم عربي → عرض القائمة → `/auth/me` → 401 بدون توكن) اشتغلت صح عبر
> `requests` حقيقي ضد السيرفر المحلي المتصل بـSupabase. بالطريق اكتُشف وانصلح تعارض
> حقيقي (bcrypt 4.1+/5.x مع passلib، راجع الكوميت). `backend/.env` (غير مرفوع لـgit)
> فيه بيانات الاتصال الفعلية الآن. `frontend/`: Login وStores مبنيّتين، باقي الشاشات
> حواجز مكان. راجع `backend/README.md` و`frontend/README.md` للتشغيل.
>
> **المتبقي قبل إكمال المرحلة 1:** تثبيت Node.js محلياً (مو مثبّت على هذا الجهاز) —
> بعدها نقدر نشغّل الـfrontend كمان ونكمل باقي الـAPI الحقيقي فوق منطق العمل الموجود.


## Context

DataLY is currently a Python CLI + Excel-file-based tool (this repo) that processes supplier invoices for grocery/retail stores: extracts items from a raw invoice, cleans them, runs a merchant "receiving session" (barcode/expiry/price entry via a Streamlit form), reconciles item names/categories against known data, and exports an Alsahl-POS-compatible purchase file. It works — this session validated the full pipeline end-to-end against real invoices and fixed several real bugs along the way (nullable `per_box` handling, supplier-name detection, barcode-based reconciliation timing, smart column detection).

The user's motivation has shifted: enthusiasm for running DataLY as a manual day-to-day business dipped, and they've decided to sell the Alsahl POS license and instead build toward a data-analyst career. Rather than abandon DataLY, they want to turn it into a **complete, well-documented, live-hosted web application** — a strong portfolio piece proving real engineering ability — before shifting focus to data analysis learning and growing their professional presence (Facebook/LinkedIn).

Three scope decisions are locked in: **live hosted app with a real URL**, **PostgreSQL** (deliberately, as a learning goal), **multi-store from day one** (not bolted on later). Stack: FastAPI backend (reusing the existing, field-tested pandas business logic almost unchanged) + PostgreSQL + React frontend.

The existing codebase's business logic is not arbitrary — it encodes real decisions made against real invoice data this session (e.g., barcode is the identity anchor because name phrasing varies by supplier; every reconciliation match needs human approval because confidence scores alone produced real false positives like "كورن"≈"كلور" at 85.7% similarity and a 67%-similar match between two products 10x different in size; `per_box` must stay nullable because a fabricated default of `1` looks like real data and silently corrupts downstream box-count math). The rebuild's job is to carry that logic into a proper multi-user, database-backed, deployed system without losing any of it.

## Recommended Approach

### 0. Where this lives

New `backend/` and `frontend/` directories alongside the existing modules in this same repo. The existing CLI code (`main.py`, `extractors/`, `transformers/`, `fusion/`, `session/`, `adapters/`, `utils/`) stays untouched and working throughout the port — it's both the reference implementation and the source of logic to carry over. Nothing gets deleted until the web app fully replaces it.

### 1. Postgres schema

```sql
-- Reference data (replaces utils/categories.json)
categories (id PK, main text, sub text, UNIQUE(main, sub))
category_keywords (id PK, category_id FK, keyword text, is_whole_word boolean)

-- Tenancy
stores (id PK, name text, code text UNIQUE, created_at)
suppliers (id PK, name text UNIQUE, created_at)   -- currently just a free-text string, becomes a real entity

-- Shared, accumulating catalog (replaces master_items.xlsx read-only pattern + barcode_categories.json)
product_catalog (
  id PK, barcode varchar(64) UNIQUE NOT NULL,   -- VARCHAR, never integer — leading zeros / non-numeric prefixes matter
  canonical_name text NOT NULL,
  category_id FK NULL,
  source_store_id FK NULL,
  updated_at
)

-- Invoice pipeline
invoices (
  id PK, store_id FK NOT NULL, supplier_id FK NULL, supplier_name_raw text,
  method smallint NOT NULL CHECK (method IN (1,2)),
  status text NOT NULL,   -- uploaded|cleaned|session_pending|session_complete|reconciled|merged|exported
  raw_file_path text, original_filename text, uploaded_by FK NULL, uploaded_at, notes text
)

invoice_items (
  id PK, invoice_id FK NOT NULL, item_order int,
  item_name text NOT NULL, category_id FK NULL,
  unit_text text, quantity_pieces numeric(12,3) NOT NULL,   -- ALWAYS individual pieces, never boxes
  per_box integer NULL,                                      -- nullable end-to-end; NULL = genuinely unknown
  box_count numeric(12,4) GENERATED ALWAYS AS
      (CASE WHEN per_box IS NOT NULL AND per_box > 0
            THEN quantity_pieces / per_box ELSE NULL END) STORED,  -- explicit IS NOT NULL check, never `or 1`
  unit_cost numeric(12,3), total_price numeric(12,3), discount_pct numeric(6,4),
  expiry_date date NULL, supplier_item_code text, barcode varchar(64) NULL
)

sessions (id PK, invoice_id FK UNIQUE NOT NULL, method smallint, status text, created_at, completed_at)

session_items (
  id PK, session_id FK NOT NULL, invoice_item_id FK NOT NULL,
  barcode varchar(64) NULL, expiration_date date NULL, sale_price numeric(12,3) NULL,
  is_complete boolean NOT NULL DEFAULT false
)

-- Reconciliation audit trail (replaces the ephemeral pending_matches list + 3 duplicate terminal-prompt flows)
reconciliation_matches (
  id PK, invoice_item_id FK NOT NULL,
  match_method text NOT NULL,      -- 'barcode' | 'fuzzy_name'
  matched_barcode varchar(64) NULL, suggested_name text, suggested_category_id FK NULL,
  similarity_score numeric(5,1), warning_reason text NULL,
  decision text NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|manual
  manual_name text NULL, decided_by FK NULL, decided_at timestamptz NULL
)

-- Cumulative per-store inventory, lot-level (replaces old_inventory.xlsx)
inventory_lots (
  id PK, store_id FK NOT NULL, barcode varchar(64) NOT NULL, item_name text,
  expiration_date date NULL, quantity numeric(12,3), unit_cost numeric(12,3),
  last_invoice_item_id FK NULL, updated_at
)
-- same barcode can arrive in multiple batches/expiry dates — one lot per (store, barcode, expiry):
CREATE UNIQUE INDEX ux_inventory_lot ON inventory_lots
  (store_id, barcode, COALESCE(expiration_date, DATE '9999-12-31'));

alsahl_exports (id PK, invoice_id FK NOT NULL, file_path text, exported_at)
users (id PK, email text UNIQUE, hashed_password text, created_at)   -- single-admin auth, see §5
```

Source-of-truth mapping: `product_catalog` ← `master_items.xlsx` + `utils/barcode_categories.json`; `category_keywords` ← `utils/categories.json`; `inventory_lots` ← `data/<store>/old_inventory.xlsx`; `invoices`/`invoice_items` ← `invoice_data.xlsx`; `session_items` ← `session_output.xlsx`; `reconciliation_matches` ← the in-memory `pending_matches` list in `fusion/reconciliation.py`.

### 2. Backend architecture

```
backend/app/
  core/{config.py, security.py, db.py}
  models/            # SQLAlchemy ORM mirroring the schema above
  schemas/           # Pydantic
  api/routes/{auth,stores,invoices,sessions,reconciliation,inventory,catalog,exports}.py
  services/          # invoice_service, session_service, reconciliation_service, export_service
  core_logic/        # ported business logic — see mapping below
  alembic/
```

**Carried over nearly unchanged** (pure DataFrame/logic functions — no behavior change, only their I/O boundary moves from Excel files to DB rows):
- [transformers/base_cleaner.py](transformers/base_cleaner.py) `clean_data()` — unchanged, still DataFrame in/out.
- [utils/validators.py](utils/validators.py) — unchanged; `InvoiceValidationError` messages (already Arabic, already user-facing) become the FastAPI 422 response bodies.
- [fusion/reconciliation.py](fusion/reconciliation.py) `reconcile_dataframes()` and `_merge_duplicate_barcodes()` — already written pure/testable; carry over verbatim into `reconciliation_service`.
- [extractors/excel_extractor.py](extractors/excel_extractor.py) `POSSIBLE_COLUMNS`, `detect_header_row()`, `extract_supplier_name()` — pure; only the `pd.read_excel()` call source changes (uploaded file bytes instead of a path).
- [extractors/inventory_extractor.py](extractors/inventory_extractor.py) `detect_inventory_columns()`, `detect_subcategory_column()` — unchanged column-detection heuristics.
- [utils/categorizer.py](utils/categorizer.py) `get_category()` matching algorithm (word index, length-scaled fuzzy thresholds 92/88/85) — unchanged logic; only its data source changes (JSON file → `categories`/`category_keywords` tables).
- [session/session_generator.py](session/session_generator.py) `calc_per_box`, `calc_unit_cost`, `calc_total`, `calc_box_count`, the per-box regexes (`كرتون 24`, `(24)`, bare-number fallback) — unchanged computation, now populates `invoice_items` rows via INSERT instead of an xlsxwriter file.
- [fusion/merge.py](fusion/merge.py) `get_per_box()` — same rule, now an ORM join instead of `pd.merge` on two Excel files.
- [adapters/alsahl_adapter.py](adapters/alsahl_adapter.py) — column order, formats, and the "leave `العبوة` blank when `per_box` unknown" rule carry over exactly; becomes `export_service.export_to_alsahl()` reading DB rows.
- [fusion/inventory_manager.py](fusion/inventory_manager.py) `update_inventory()`'s dedup rule (same barcode+expiration = same lot, latest wins) becomes an `ON CONFLICT (store_id, barcode, COALESCE(expiration_date,...)) DO UPDATE` upsert.

**Rewritten / retired**:
- `main.py` CLI orchestration → FastAPI routes + services.
- [session/receiving_app.py](session/receiving_app.py) (Streamlit) → React intake screens (§4).
- [fusion/inventory_matcher.py](fusion/inventory_matcher.py) and [fusion/supplier_matcher.py](fusion/supplier_matcher.py) duplicate `reconciliation.py`'s approve/reject/rename flow at an earlier stage — **retire both**. Method 2's useful part, `enrich_invoice_from_supplier()`'s fuzzy pre-fill of barcode/expiration from the supplier file, is kept only as a pre-fill for the intake form's default values. Every "is this the same item" human decision routes through the one `reconciliation_matches` table/screen, post-intake — matching `ARCHITECTURE.md`'s own stated reasoning for why reconciliation happens after the merchant fills in the barcode.
- [utils/barcode_categories.py](utils/barcode_categories.py) and the JSON-file half of `categorizer.py` → replaced by `product_catalog`/`category_keywords` repository reads.
- Every `os.path.join("data", store_id, ...)` path → DB reads/writes. Only two files remain on disk/object storage: the originally uploaded invoice (audit trail) and the generated Alsahl export.

### 3. API endpoints

```
POST   /auth/login                                    GET  /auth/me
GET/POST  /stores                                      GET/POST /suppliers
POST   /stores/{store_id}/invoices                      (upload; runs extract_from_excel + detect_method)
POST   /invoices/{id}/clean                             (runs clean_data + validators, persists invoice_items)
GET    /invoices/{id}/items       PATCH /invoices/{id}/items/{item_id}
POST   /invoices/{id}/session                           (creates session, pre-fills method-2 barcode/expiry)
GET    /sessions/{id}             PATCH /sessions/{id}/items/{item_id}
POST   /sessions/{id}/complete                          (triggers reconcile_dataframes())
GET    /invoices/{id}/reconciliation-matches
POST   /reconciliation-matches/{id}/decide               {decision: approve|reject|manual, manual_name?}
POST   /invoices/{id}/merge                              (merge + upsert inventory_lots + learn product_catalog)
POST   /invoices/{id}/export      GET /invoices/{id}/export/download
GET    /stores/{store_id}/inventory     GET /stores/{store_id}/invoices
GET    /product-catalog?barcode=|q=
```

### 4. React frontend

Vite + React + TypeScript, TanStack Query, shadcn/ui + Tailwind, react-hook-form.

- `/login`
- `/stores` — store switcher/dashboard
- `/stores/:id/invoices`, `/stores/:id/invoices/new` — upload (invoice + optional supplier file + method override)
- `/invoices/:id/review` — cleaned-items grid, inline edit, validation warning banner
- `/invoices/:id/session` — **replaces `receiving_app.py`**: one-item-at-a-time card, progress bar, method-aware locked fields, sidebar quick-jump — same UX, now a real web form instead of a download/re-upload round-trip
- `/invoices/:id/reconciliation` — **replaces `resolve_matches_interactively()` and the two duplicate terminal flows**: each pending match shows invoice name vs. suggested name, similarity %, warning banner, Accept / Reject / Manual-rename actions
- `/invoices/:id/export` — merge summary, generate + download Alsahl file, export history
- `/stores/:id/inventory` — inventory lots table (barcode, name, expiry, qty) — new, nothing viewed this before
- `/stores/:id/history` — past invoices timeline

### 5. Auth

Lightweight single-admin login (JWT, one `users` row to start) protecting all endpoints — added in Phase 3, right before the URL goes public. Not zero-auth (real cost/pricing data on a public URL is a portfolio red flag and a real exposure), not full multi-user RBAC (this app has one operator; that's scope it doesn't need). `store_id` stays a data-partitioning dimension (a dropdown for the one authenticated user), not an auth boundary — keeps Phases 1–2 auth-free for fast local iteration.

### 6. Hosting

**Vercel (frontend, free) + Render (FastAPI backend, free web service) + Supabase (Postgres, free tier).** Render's own free Postgres now auto-expires after 30 days, which would force a mid-project migration; Supabase's free Postgres is durable long-term and includes a table browser (a genuine bonus for the "learn Postgres" goal), and connects cleanly to a Render web service via `DATABASE_URL`. Steady-state cost: $0/mo (Render free tier cold-starts after inactivity — fine for a portfolio demo; upgrade to $7/mo later only if that becomes annoying). Env vars: `DATABASE_URL` (Supabase), `JWT_SECRET`, `CORS_ORIGINS` (Vercel domain), frontend's `VITE_API_URL` (Render domain).

### 7. Migration

This worktree's `data/` only has empty test folders — no real data here. The user's **main checkout** (`C:\Users\naji2\DataLY_6`, not this worktree) currently has a real, verified `data/old_inventory.xlsx` (825 items, restored and validated this session) and `utils/barcode_categories.json`. Before finishing Phase 1, write a one-time `scripts/migrate_legacy_data.py` (run manually, not part of the deployed app) that: (1) reads `data/old_inventory.xlsx` via the carried-over `extract_old_inventory()` logic and upserts into a `stores` row + `inventory_lots`; (2) bulk-inserts `utils/barcode_categories.json` into `product_catalog`; (3) seeds `categories`/`category_keywords` from `utils/categories.json` (32 entries, 4 main categories) via an Alembic data migration.

### 8. Phased milestones

- **Phase 0 (0.5–1 day):** Scaffold `backend/` (FastAPI, Alembic, docker-compose Postgres) and `frontend/` (Vite React TS) alongside the existing CLI code.
- **Phase 1 (1–2 weeks):** Schema + backend core + one full flow working locally via Swagger UI only (upload → clean → session → fill item → complete → reconciliation decide → merge → export), no frontend, no auth yet. Adapt the 4 existing test files. Proves business-logic reuse works before any UI investment.
- **Phase 2 (2–3 weeks):** Build React screens against the Phase 1 API, in order: upload/review → session intake → reconciliation screen → export/download → inventory/history.
- **Phase 3 (3–5 days):** Deploy — Supabase Postgres, Render backend, Vercel frontend, wire env vars/CORS, add the single-admin login before sharing the URL, run the migration script.
- **Phase 4 (ongoing):** Polish — inventory filters, category-keyword admin screen, mobile pass on the session screen (merchants use phones), portfolio README/architecture writeup, seed demo data so recruiters can explore without uploading real files.

### 9. Testing carryover

- [tests/test_base_cleaner.py](tests/test_base_cleaner.py) — carries over verbatim.
- [tests/test_reconciliation.py](tests/test_reconciliation.py) — `reconcile_dataframes()`/`_merge_duplicate_barcodes()` tests carry over verbatim; the `resolve_matches_interactively()` tests become `TestClient` calls against `POST /reconciliation-matches/{id}/decide`.
- [tests/test_categorizer.py](tests/test_categorizer.py) — same assertions (including the "كورن"≈"كلور" collision guard), fixtures switch to a seeded test-DB session.
- [tests/test_barcode_categories.py](tests/test_barcode_categories.py) — same `lookup`/`learn` semantics against a transactional test-DB fixture.
- New: FastAPI integration tests for the full upload→export flow, an Alembic migration smoke test, an explicit test for the `inventory_lots` NULL-expiration unique-index behavior.

## Verification

- **Phase 1 exit criteria:** the full pipeline (upload → clean → session → reconciliation → merge → export) runs successfully through Swagger UI (`/docs`) against a real invoice file, producing a downloadable Alsahl-format export byte-identical in structure to the current CLI's output. Re-run the ported test suite (`pytest`) — all previously-passing assertions must still pass.
- **Phase 2 exit criteria:** the same flow completes end-to-end through the React UI with no direct API calls needed; the session screen and reconciliation screen are usable on a phone-width viewport (merchants use phones).
- **Phase 3 exit criteria:** the live Vercel URL loads, requires login, and a full upload→export cycle works against the deployed Supabase database from a completely fresh browser session.
- **Data integrity check:** after running the migration script, `SELECT COUNT(*) FROM inventory_lots` matches the row count of the source `old_inventory.xlsx`, and spot-check a handful of barcodes' categories against `product_catalog` vs. the original `barcode_categories.json`.
