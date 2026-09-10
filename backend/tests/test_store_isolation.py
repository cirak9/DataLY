import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.db import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.export import AlsahlExport
from app.models.invoice import Invoice, InvoiceItem
from app.models.inventory import InventoryLot
from app.models.reconciliation import ReconciliationMatch
from app.models.session import IntakeSession, SessionItem
from app.models.store import Store
from app.models.user import User

"""
عزل بيانات العملاء — يعيد بالتحديد نفس خطوات التحقق الحي اللي صارت يدوياً بـcurl
ضد Supabase الحقيقية (حساب demo@dataly.app مقابل الحساب الإداري) كاختبارات آلية،
ويغطّي بعدها بقية دوال get_owned_* بـapp/api/deps.py اللي ما اتحققت حياً وقتها
(الجلسة وتسوية الأصناف — أعمق سلسلة join بالنظام كله: تطابق → صنف فاتورة → فاتورة
→ متجر)، وباقي نقاط الـAPI المتفرعة من متجر (دمج، تصدير، تنزيل، مخزون). كل مستخدم
يشوف بياناته بس، وأي محاولة وصول مباشر لبيانات مستخدم ثاني ترجع 404 — لا 403،
عشان ما نسرّب حتى معلومة وجود الـID.

قاعدة بيانات SQLite بالذاكرة. جدول inventory_lots يُنشأ بدون فهرسه الفريد المركّب
(يستخدم تعبير COALESCE/DATE خاص بـPostgres، راجع app/models/inventory.py، مو مدعوم
بـSQLite) — اختبارات العزل هون ما تحتاج قيد التفرّد نفسه، بس تحتاج الجدول موجود
لاختبار مسار الوصول الناجح لصاحب المتجر.
"""

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_inventory_lots_table = Base.metadata.tables["inventory_lots"]
_pg_only_index = next(ix for ix in _inventory_lots_table.indexes if ix.name == "ux_inventory_lot")
_inventory_lots_table.indexes.discard(_pg_only_index)

Base.metadata.create_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def two_owners():
    """مستخدمان، كل وحد عنده متجر خاص فيه فاتورة واحدة — يرجّع التوكنات والمعرّفات."""
    db = TestingSessionLocal()
    try:
        user_a = User(email="owner-a@dataly-isolation-test.com", hashed_password=hash_password("pass-a-123"))
        user_b = User(email="owner-b@dataly-isolation-test.com", hashed_password=hash_password("pass-b-123"))
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        store_a = Store(name="متجر أ", code="TEST-A", owner_id=user_a.id)
        store_b = Store(name="متجر ب", code="TEST-B", owner_id=user_b.id)
        db.add_all([store_a, store_b])
        db.commit()
        db.refresh(store_a)
        db.refresh(store_b)

        invoice_a = Invoice(store_id=store_a.id, method=1, status="uploaded")
        invoice_b = Invoice(store_id=store_b.id, method=1, status="uploaded")
        db.add_all([invoice_a, invoice_b])
        db.commit()
        db.refresh(invoice_a)
        db.refresh(invoice_b)

        item_a = InvoiceItem(invoice_id=invoice_a.id, item_order=1, item_name="صنف أ", quantity_pieces=10)
        item_b = InvoiceItem(invoice_id=invoice_b.id, item_order=1, item_name="صنف ب", quantity_pieces=10)
        db.add_all([item_a, item_b])
        db.commit()
        db.refresh(item_a)
        db.refresh(item_b)

        session_a = IntakeSession(invoice_id=invoice_a.id, method=1, status="pending")
        session_b = IntakeSession(invoice_id=invoice_b.id, method=1, status="pending")
        db.add_all([session_a, session_b])
        db.commit()
        db.refresh(session_a)
        db.refresh(session_b)

        session_item_a = SessionItem(session_id=session_a.id, invoice_item_id=item_a.id)
        session_item_b = SessionItem(session_id=session_b.id, invoice_item_id=item_b.id)
        db.add_all([session_item_a, session_item_b])
        db.commit()
        db.refresh(session_item_a)
        db.refresh(session_item_b)

        match_a = ReconciliationMatch(invoice_item_id=item_a.id, match_method="barcode", decision="pending")
        match_b = ReconciliationMatch(invoice_item_id=item_b.id, match_method="barcode", decision="pending")
        db.add_all([match_a, match_b])
        db.commit()
        db.refresh(match_a)
        db.refresh(match_b)

        # سجل تصدير جاهز لفاتورة أ بس — يتيح اختبار تنزيل ناجح لصاحبها الحقيقي
        # (بدون الحاجة لتمرير الفاتورة فعلياً بكل حالات خط الأنابيب أولاً؛ build_export_bytes
        # يبني الملف من الصفوف الموجودة مباشرة، بغض النظر عن حالة الفاتورة).
        export_a = AlsahlExport(invoice_id=invoice_a.id, file_path="/tmp/unused.xlsx")
        db.add(export_a)
        db.commit()
        db.refresh(export_a)

        lot_a = InventoryLot(store_id=store_a.id, barcode="TESTLOT001", item_name="صنف مخزون أ", quantity=5)
        db.add(lot_a)
        db.commit()
        db.refresh(lot_a)

        token_a = client.post(
            "/auth/login", json={"email": user_a.email, "password": "pass-a-123"}
        ).json()["access_token"]
        token_b = client.post(
            "/auth/login", json={"email": user_b.email, "password": "pass-b-123"}
        ).json()["access_token"]

        yield {
            "store_a": store_a.id,
            "store_b": store_b.id,
            "invoice_a": invoice_a.id,
            "invoice_b": invoice_b.id,
            "item_a": item_a.id,
            "item_b": item_b.id,
            "session_a": session_a.id,
            "session_b": session_b.id,
            "session_item_a": session_item_a.id,
            "session_item_b": session_item_b.id,
            "match_a": match_a.id,
            "match_b": match_b.id,
            "lot_a": lot_a.id,
            "token_a": token_a,
            "token_b": token_b,
        }
    finally:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        db.close()


def test_list_stores_only_shows_own(two_owners):
    d = two_owners
    ids = [s["id"] for s in client.get("/stores", headers=_auth(d["token_a"])).json()]
    assert d["store_a"] in ids
    assert d["store_b"] not in ids


def test_cannot_fetch_other_owners_store_directly(two_owners):
    d = two_owners
    resp = client.get(f"/stores/{d['store_b']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_fetch_own_store(two_owners):
    d = two_owners
    resp = client.get(f"/stores/{d['store_a']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 200


def test_cannot_list_invoices_of_other_owners_store(two_owners):
    d = two_owners
    resp = client.get(f"/stores/{d['store_b']}/invoices", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_cannot_fetch_other_owners_invoice_by_id(two_owners):
    """يغطّي نفس مستوى التحقق اللي صار على invoices/{id} مباشرة (قفزة join عبر الفاتورة للمتجر)."""
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_b']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_fetch_own_invoice_by_id(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_a']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 200


def test_isolation_is_symmetric_for_the_other_owner(two_owners):
    """نفس الفحص من الاتجاه المعاكس — يطابق التحقق الحي اللي صار بالاتجاهين بالضبط."""
    d = two_owners
    assert client.get(f"/stores/{d['store_a']}", headers=_auth(d["token_b"])).status_code == 404
    assert client.get(f"/invoices/{d['invoice_a']}", headers=_auth(d["token_b"])).status_code == 404
    assert client.get(f"/stores/{d['store_b']}", headers=_auth(d["token_b"])).status_code == 200


def test_new_store_is_owned_by_its_creator(two_owners):
    d = two_owners
    created = client.post(
        "/stores", json={"name": "متجر جديد", "code": "TEST-NEW"}, headers=_auth(d["token_a"])
    )
    assert created.status_code == 201
    new_store_id = created.json()["id"]

    assert client.get(f"/stores/{new_store_id}", headers=_auth(d["token_a"])).status_code == 200
    assert client.get(f"/stores/{new_store_id}", headers=_auth(d["token_b"])).status_code == 404


# ---------------------------------------------------------------------------
# جلسة الاستلام — get_owned_session يوصل للمتجر بقفزتين join (جلسة → فاتورة → متجر)
# ---------------------------------------------------------------------------

def test_cannot_fetch_other_owners_session_by_id(two_owners):
    d = two_owners
    resp = client.get(f"/sessions/{d['session_b']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_fetch_own_session_by_id(two_owners):
    d = two_owners
    resp = client.get(f"/sessions/{d['session_a']}", headers=_auth(d["token_a"]))
    assert resp.status_code == 200


def test_cannot_get_session_via_other_owners_invoice(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_b']}/session", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_cannot_patch_other_owners_session_item(two_owners):
    d = two_owners
    resp = client.patch(
        f"/sessions/{d['session_b']}/items/{d['session_item_b']}",
        json={"barcode": "999", "sale_price": 5.5},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 404


def test_can_patch_own_session_item(two_owners):
    d = two_owners
    resp = client.patch(
        f"/sessions/{d['session_a']}/items/{d['session_item_a']}",
        json={"barcode": "999", "sale_price": 5.5},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 200


def test_cannot_complete_other_owners_session(two_owners):
    d = two_owners
    resp = client.post(f"/sessions/{d['session_b']}/complete", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# التسوية — get_owned_reconciliation_match يوصل للمتجر بثلاث قفزات join
# (تطابق → صنف فاتورة → فاتورة → متجر)، أعمق سلسلة بالنظام كله
# ---------------------------------------------------------------------------

def test_cannot_list_reconciliation_matches_of_other_owners_invoice(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_b']}/reconciliation-matches", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_list_own_reconciliation_matches(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_a']}/reconciliation-matches", headers=_auth(d["token_a"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_cannot_decide_other_owners_reconciliation_match(two_owners):
    d = two_owners
    resp = client.post(
        f"/reconciliation-matches/{d['match_b']}/decide",
        json={"decision": "reject"},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 404


def test_can_decide_own_reconciliation_match(two_owners):
    d = two_owners
    resp = client.post(
        f"/reconciliation-matches/{d['match_a']}/decide",
        json={"decision": "reject"},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "rejected"


# ---------------------------------------------------------------------------
# الدمج والتصدير — نفس get_owned_invoice، بس على نقاط API مختلفة (مسارات منفصلة
# فعلياً بالكود، لازم كل وحدة تتحقق لحالها لضمان محد يفوّت التحقق مستقبلاً).
# الفاتورتان بحالة "uploaded" بالفكستشر — أبعد ما يكون عن reconciled/merged،
# فلو التحقق من الملكية فشل بالغلط بيرجّع 404 مباشرة قبل أي فحص حالة؛ لو نجح
# ووصل لمنطق العمل، يرجّع 422 (حالة غلط) مو 404 — هذا الفرق (404 مقابل 422)
# هو دليل إن التحقق من الملكية هو اللي سمح/منع الوصول، مو صدفة.
# ---------------------------------------------------------------------------

def test_cannot_merge_other_owners_invoice(two_owners):
    d = two_owners
    resp = client.post(f"/invoices/{d['invoice_b']}/merge", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_merging_own_invoice_passes_ownership_check(two_owners):
    d = two_owners
    resp = client.post(f"/invoices/{d['invoice_a']}/merge", headers=_auth(d["token_a"]))
    assert resp.status_code == 422  # حالة الفاتورة "uploaded" مو "reconciled" — خطأ عمل، مو ملكية


def test_cannot_export_other_owners_invoice(two_owners):
    d = two_owners
    resp = client.post(f"/invoices/{d['invoice_b']}/export", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_exporting_own_invoice_passes_ownership_check(two_owners):
    d = two_owners
    resp = client.post(f"/invoices/{d['invoice_a']}/export", headers=_auth(d["token_a"]))
    assert resp.status_code == 422  # حالة الفاتورة "uploaded" مو ضمن merged/exported — خطأ عمل، مو ملكية


def test_cannot_download_other_owners_export(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_b']}/export/download", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_download_own_export(two_owners):
    d = two_owners
    resp = client.get(f"/invoices/{d['invoice_a']}/export/download", headers=_auth(d["token_a"]))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------------------------
# المخزون — get_owned_store مباشرة (نفس دالة GET /stores/{id})، بس مسار/جدول مختلف
# ---------------------------------------------------------------------------

def test_cannot_list_inventory_of_other_owners_store(two_owners):
    d = two_owners
    resp = client.get(f"/stores/{d['store_b']}/inventory", headers=_auth(d["token_a"]))
    assert resp.status_code == 404


def test_can_list_own_store_inventory(two_owners):
    d = two_owners
    resp = client.get(f"/stores/{d['store_a']}/inventory", headers=_auth(d["token_a"]))
    assert resp.status_code == 200
    lots = resp.json()
    assert len(lots) == 1
    assert lots[0]["id"] == d["lot_a"]


# ---------------------------------------------------------------------------
# رفع فاتورة — get_owned_store أيضاً، بس هون قبل ما يوصل الطلب لجسم الدالة أصلاً
# (الملف نفسه محتاج يكون موجود بالطلب عشان FastAPI يقبل الشكل، بس save_uploaded_invoice
# ما تُستدعى إطلاقاً لو الملكية فشلت — نفس ترتيب باقي نقاط get_owned_invoice).
# ---------------------------------------------------------------------------

def test_cannot_upload_invoice_to_other_owners_store(two_owners):
    d = two_owners
    resp = client.post(
        f"/stores/{d['store_b']}/invoices",
        files={"file": ("fake.xlsx", b"not a real workbook", "application/octet-stream")},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 404


def test_can_upload_invoice_to_own_store(two_owners):
    d = two_owners
    resp = client.post(
        f"/stores/{d['store_a']}/invoices",
        files={"file": ("fake.xlsx", b"not a real workbook", "application/octet-stream")},
        headers=_auth(d["token_a"]),
    )
    # save_uploaded_invoice يتحقق من امتداد الملف بس بهالمرحلة (التحليل الفعلي بخطوة
    # /clean منفصلة) — 201 نجاح كامل يثبت وصول الملكية والحفظ، مو مجرد تجاوز 404.
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "uploaded"


def test_uploading_with_unsupported_extension_still_passes_ownership_check(two_owners):
    """امتداد مرفوض (422) لا 404 — يثبت إن رفض الملكية مو السبب حتى بمسار الخطأ."""
    d = two_owners
    resp = client.post(
        f"/stores/{d['store_a']}/invoices",
        files={"file": ("fake.txt", b"not excel at all", "text/plain")},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# الموردون — عكس كل ما سبق تماماً: /suppliers مشترك عمداً بين كل الحسابات، بلا
# owner_id إطلاقاً (راجع app/models/store.py وbackend/README.md — نفس فلسفة
# product_catalog/التصنيفات: فهرس عام، مو بيانات تجارية خاصة بمتجر). الاختبارات
# هون تثبّت هذا القرار كسلوك متوقَّع ومحمي من رجوع خطأ يضيف عزل غير مقصود له
# مستقبلاً — مو ثغرة، تصميم صريح.
# ---------------------------------------------------------------------------

def test_supplier_created_by_one_owner_is_visible_to_another(two_owners):
    d = two_owners
    created = client.post(
        "/suppliers", json={"name": "مورد مشترك بين المتاجر"}, headers=_auth(d["token_a"])
    )
    assert created.status_code == 201
    supplier_id = created.json()["id"]

    listed_by_b = client.get("/suppliers", headers=_auth(d["token_b"])).json()
    assert any(s["id"] == supplier_id for s in listed_by_b)


def test_creating_same_supplier_name_twice_returns_the_same_row(two_owners):
    d = two_owners
    first = client.post(
        "/suppliers", json={"name": "مورد مكرر"}, headers=_auth(d["token_a"])
    ).json()
    second = client.post(
        "/suppliers", json={"name": "مورد مكرر"}, headers=_auth(d["token_b"])
    ).json()
    assert first["id"] == second["id"]


def test_suppliers_endpoints_require_auth():
    assert client.get("/suppliers").status_code == 401
    assert client.post("/suppliers", json={"name": "بدون تسجيل دخول"}).status_code == 401


# ---------------------------------------------------------------------------
# استيراد المخزون القديم — get_owned_store، نفس نمط رفع الفاتورة تماماً.
#
# ملاحظة مهمة: نجاح كامل (201 + upsert حقيقي بـinventory_lots) ما يُختبر هون —
# استعلام الـupsert (نفس اللي بـmerge_service.py أصلاً) يستخدم صياغة SQL خاصة
# بـPostgres (ON CONFLICT مع COALESCE/DATE) ما تشتغل على SQLite، فنفس القيد
# الموجود أصلاً على اختبارات الدمج (merge) ينطبق هنا. الفحص الوحيد الممكن محلياً
# هو حدود الملكية (404/422 قبل ما يوصل الطلب للـSQL) — النجاح الكامل يتحقق منه
# حياً ضد Supabase الحقيقية، ومنطق الاستخراج/كشف الأعمدة له اختبارات مستقلة
# بدون قاعدة بيانات إطلاقاً بـtest_inventory_extractor.py.
# ---------------------------------------------------------------------------

def _make_old_inventory_xlsx(rows: list[tuple]) -> bytes:
    import io
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["الباركود", "اسم الصنف", "الصلاحية", "الكمية"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_cannot_import_inventory_to_other_owners_store(two_owners):
    d = two_owners
    content = _make_old_inventory_xlsx([("TESTIMP001", "صنف مستورد", "2027-01-01", 10)])
    resp = client.post(
        f"/stores/{d['store_b']}/inventory/import",
        files={"file": ("old_inventory.xlsx", content, "application/octet-stream")},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 404


def test_importing_unsupported_file_type_passes_ownership_check(two_owners):
    """امتداد مرفوض (422) لا 404 — نفس نمط التفريق المعتمد بباقي رفع الملفات
    (يتحقق قبل ما يوصل الطلب لاستعلام الـSQL الخاص بـPostgres أصلاً)."""
    d = two_owners
    resp = client.post(
        f"/stores/{d['store_a']}/inventory/import",
        files={"file": ("old_inventory.csv", b"barcode,name\n123,test", "text/csv")},
        headers=_auth(d["token_a"]),
    )
    assert resp.status_code == 422
