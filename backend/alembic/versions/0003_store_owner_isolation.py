"""عزل بيانات العملاء: عمود stores.owner_id — كل متجر مملوك لمستخدم واحد بدل ما
يشوف أي مستخدم مسجّل دخول كل المتاجر (راجع app/api/deps.py للتحقق من الملكية)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("owner_id", sa.Integer(), nullable=True))

    # تعبئة الملكية للمتاجر الموجودة مسبقاً (قبل ما يصير العمود إجباري): متجر الديمو
    # العام لحساب demo@dataly.app، وأي متجر ثاني (بيانات صاحب المشروع الحقيقية) لحساب
    # holohood4@gmail.com — أول مستخدم مسجّل بالنظام أصلاً (المستخدم الإداري الوحيد
    # قبل هذا التحديث).
    op.execute(
        """
        UPDATE stores SET owner_id = (SELECT id FROM users WHERE email = 'demo@dataly.app')
        WHERE code = 'WAHA'
        """
    )
    op.execute(
        """
        UPDATE stores SET owner_id = (SELECT id FROM users ORDER BY id ASC LIMIT 1)
        WHERE owner_id IS NULL
        """
    )

    op.alter_column("stores", "owner_id", nullable=False)
    op.create_foreign_key(
        "fk_stores_owner_id_users", "stores", "users", ["owner_id"], ["id"]
    )
    op.create_index("ix_stores_owner_id", "stores", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_stores_owner_id", table_name="stores")
    op.drop_constraint("fk_stores_owner_id_users", "stores", type_="foreignkey")
    op.drop_column("stores", "owner_id")
