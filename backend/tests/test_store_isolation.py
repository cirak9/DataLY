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
from app.models.invoice import Invoice
from app.models.store import Store
from app.models.user import User

"""
عزل بيانات العملاء — يعيد بالتحديد نفس خطوات التحقق الحي اللي صارت يدوياً بـcurl
ضد Supabase الحقيقية (حساب demo@dataly.app مقابل الحساب الإداري) كاختبارات آلية:
كل مستخدم يشوف متجره بس، وأي محاولة وصول مباشر (متجر أو فاتورة) لبيانات مستخدم
ثاني ترجع 404 — لا 403، عشان ما نسرّب حتى معلومة وجود الـID.

قاعدة بيانات SQLite بالذاكرة، باستثناء جدول inventory_lots — فهرسه الفريد يستخدم
تعبير COALESCE/DATE خاص بـPostgres (راجع app/models/inventory.py) مو مدعوم بـSQLite،
واختبارات العزل هون ما تحتاج جدول المخزون أصلاً (تغطي مستوى المتجر والفاتورة فقط،
نفس نطاق التحقق الحي اللي صار).
"""

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(
    bind=engine, tables=[t for t in Base.metadata.sorted_tables if t.name != "inventory_lots"]
)


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
            "token_a": token_a,
            "token_b": token_b,
        }
    finally:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != "inventory_lots":
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
