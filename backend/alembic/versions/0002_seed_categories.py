"""بذر categories/category_keywords من app/core_logic/categories_seed.json
(نسخة مطابقة لـutils/categories.json بالأداة الأصلية — راجع docs/REBUILD_PLAN.md قسم 7)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11

"""
import json
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SEED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "app", "core_logic", "categories_seed.json"
)

categories_table = sa.table(
    "categories",
    sa.column("id", sa.Integer),
    sa.column("main", sa.String),
    sa.column("sub", sa.String),
)
category_keywords_table = sa.table(
    "category_keywords",
    sa.column("category_id", sa.Integer),
    sa.column("keyword", sa.String),
    sa.column("is_whole_word", sa.Boolean),
)


def upgrade() -> None:
    with open(_SEED_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)["categories"]

    conn = op.get_bind()
    for entry in entries:
        result = conn.execute(
            categories_table.insert()
            .values(main=entry["main"], sub=entry["sub"])
            .returning(categories_table.c.id)
        )
        category_id = result.scalar_one()

        whole_word_set = set(entry.get("whole_word_keywords", []))
        keywords = entry.get("keywords", [])
        if not keywords:
            continue
        conn.execute(
            category_keywords_table.insert(),
            [
                {"category_id": category_id, "keyword": kw, "is_whole_word": kw in whole_word_set}
                for kw in keywords
            ],
        )


def downgrade() -> None:
    op.execute("DELETE FROM category_keywords")
    op.execute("DELETE FROM categories")
