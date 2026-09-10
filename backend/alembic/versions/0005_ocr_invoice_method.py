"""فاتورة عبر صور OCR: طريقة رفع جديدة method=3 (بجانب 1 يدوي، 2 إثراء مورد)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_invoice_method", "invoices", type_="check")
    op.create_check_constraint("ck_invoice_method", "invoices", "method IN (1, 2, 3)")


def downgrade() -> None:
    op.drop_constraint("ck_invoice_method", "invoices", type_="check")
    op.create_check_constraint("ck_invoice_method", "invoices", "method IN (1, 2)")
