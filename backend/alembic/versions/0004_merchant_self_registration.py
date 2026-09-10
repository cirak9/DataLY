"""تسجيل تاجر ذاتي: users.phone_number (بديل/إضافي لـemail) — البريد يصير اختياري
عشان حسابات التجار الجدد تسجّل برقم هاتف بس، بدون بريد إلكتروني إطلاقاً

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("phone_number", sa.String(32), nullable=True))
    op.create_unique_constraint("uq_users_phone_number", "users", ["phone_number"])
    op.create_index("ix_users_phone_number", "users", ["phone_number"])


def downgrade() -> None:
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_constraint("uq_users_phone_number", "users", type_="unique")
    op.drop_column("users", "phone_number")
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
