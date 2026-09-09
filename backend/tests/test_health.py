import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    """يتأكد إن التطبيق يقلع صح — بدون أي اتصال بقاعدة بيانات (health لا يلمس DB)."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_stores_requires_auth():
    """أي route محمي (get_current_user) لازم يرفض بدون توكن — 401 مو 500."""
    resp = client.get("/stores")
    assert resp.status_code == 401
