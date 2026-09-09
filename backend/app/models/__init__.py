"""
استيراد كل الموديلات هنا — Alembic (env.py) وBase.metadata.create_all() يحتاجونها
مسجّلة كلها قبل ما يقارنوا/يبنوا الجداول.
"""
from app.models.user import User
from app.models.store import Store, Supplier
from app.models.catalog import Category, CategoryKeyword, ProductCatalog
from app.models.invoice import Invoice, InvoiceItem
from app.models.session import IntakeSession, SessionItem
from app.models.reconciliation import ReconciliationMatch
from app.models.inventory import InventoryLot
from app.models.export import AlsahlExport

__all__ = [
    "User",
    "Store",
    "Supplier",
    "Category",
    "CategoryKeyword",
    "ProductCatalog",
    "Invoice",
    "InvoiceItem",
    "IntakeSession",
    "SessionItem",
    "ReconciliationMatch",
    "InventoryLot",
    "AlsahlExport",
]
