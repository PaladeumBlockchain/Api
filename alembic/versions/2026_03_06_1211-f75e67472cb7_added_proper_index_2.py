"""Added proper index (2)

Revision ID: f75e67472cb7
Revises: 2126038e0221
Create Date: 2026-03-06 12:11:01.047329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f75e67472cb7'
down_revision: Union[str, None] = '2126038e0221'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_index("ix_service_transactions_addresses", table_name="service_transactions")
    op.create_index(
        "ix_service_transactions_addresses",
        "service_transactions",
        ["addresses"],
        postgresql_using="gin",
    )

def downgrade() -> None:
    op.drop_index("ix_service_transactions_addresses", table_name="service_transactions")
    op.create_index(
        "ix_service_transactions_addresses",
        "service_transactions",
        ["addresses"],
    )
