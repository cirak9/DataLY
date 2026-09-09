"""الهجرة الأولى — كل الجداول الأساسية (راجع خطة إعادة البناء، قسم 1، لتفاصيل كل جدول)

Revision ID: 0001
Revises:
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stores_code", "stores", ["code"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("main", sa.String(100), nullable=False),
        sa.Column("sub", sa.String(100), nullable=False),
        sa.UniqueConstraint("main", "sub", name="ux_category_main_sub"),
    )

    op.create_table(
        "category_keywords",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("is_whole_word", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_category_keywords_category_id", "category_keywords", ["category_id"])
    op.create_index("ix_category_keywords_keyword", "category_keywords", ["keyword"])

    op.create_table(
        "product_catalog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("barcode", sa.String(64), nullable=False),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("source_store_id", sa.Integer, sa.ForeignKey("stores.id"), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )
    op.create_index("ix_product_catalog_barcode", "product_catalog", ["barcode"], unique=True)

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("store_id", sa.Integer, sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("supplier_name_raw", sa.String(255), nullable=True),
        sa.Column("method", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("raw_file_path", sa.String(500), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint("method IN (1, 2)", name="ck_invoice_method"),
    )
    op.create_index("ix_invoices_store_id", "invoices", ["store_id"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("item_order", sa.Integer, nullable=False),
        sa.Column("item_name", sa.Text, nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("unit_text", sa.String(255), nullable=True),
        sa.Column("quantity_pieces", sa.Numeric(12, 3), nullable=False),
        sa.Column("per_box", sa.Integer, nullable=True),
        sa.Column(
            "box_count",
            sa.Numeric(12, 4),
            sa.Computed(
                "CASE WHEN per_box IS NOT NULL AND per_box > 0 "
                "THEN quantity_pieces / per_box ELSE NULL END",
                persisted=True,
            ),
        ),
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 3), nullable=True),
        sa.Column("discount_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("supplier_item_code", sa.String(128), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    op.create_index("ix_invoice_items_barcode", "invoice_items", ["barcode"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False, unique=True),
        sa.Column("method", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "session_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column(
            "invoice_item_id", sa.Integer, sa.ForeignKey("invoice_items.id"), nullable=False, unique=True
        ),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("expiration_date", sa.Date, nullable=True),
        sa.Column("sale_price", sa.Numeric(12, 3), nullable=True),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_session_items_session_id", "session_items", ["session_id"])

    op.create_table(
        "reconciliation_matches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_item_id", sa.Integer, sa.ForeignKey("invoice_items.id"), nullable=False),
        sa.Column("match_method", sa.String(32), nullable=False),
        sa.Column("matched_barcode", sa.String(64), nullable=True),
        sa.Column("suggested_name", sa.Text, nullable=True),
        sa.Column("suggested_category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("similarity_score", sa.Numeric(5, 1), nullable=True),
        sa.Column("warning_reason", sa.Text, nullable=True),
        sa.Column("decision", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("manual_name", sa.Text, nullable=True),
        sa.Column("decided_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reconciliation_matches_invoice_item_id", "reconciliation_matches", ["invoice_item_id"])

    op.create_table(
        "inventory_lots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("store_id", sa.Integer, sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=False),
        sa.Column("item_name", sa.Text, nullable=True),
        sa.Column("expiration_date", sa.Date, nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
        sa.Column("last_invoice_item_id", sa.Integer, sa.ForeignKey("invoice_items.id"), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )
    op.create_index("ix_inventory_lots_store_id", "inventory_lots", ["store_id"])
    # صف واحد بس لكل (متجر، باركود، صلاحية) — صلاحية غير معروفة (NULL) تُعامل كقيمة
    # ثابتة بعيدة، لأن NULL != NULL بالـSQL وما كان يمنع التكرار لولا الـCOALESCE.
    op.execute(
        "CREATE UNIQUE INDEX ux_inventory_lot ON inventory_lots "
        "(store_id, barcode, COALESCE(expiration_date, DATE '9999-12-31'))"
    )

    op.create_table(
        "alsahl_exports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alsahl_exports_invoice_id", "alsahl_exports", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("alsahl_exports")
    op.execute("DROP INDEX IF EXISTS ux_inventory_lot")
    op.drop_table("inventory_lots")
    op.drop_table("reconciliation_matches")
    op.drop_table("session_items")
    op.drop_table("sessions")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("product_catalog")
    op.drop_table("category_keywords")
    op.drop_table("categories")
    op.drop_table("suppliers")
    op.drop_table("stores")
    op.drop_table("users")
