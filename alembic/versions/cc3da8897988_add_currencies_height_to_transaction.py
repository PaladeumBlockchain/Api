"""Add currencies, height to transaction

Revision ID: cc3da8897988
Revises: 043890a23408
Create Date: 2024-10-21 14:37:27.273245

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cc3da8897988"
down_revision: Union[str, None] = "043890a23408"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "service_tokens",
        sa.Column("amount", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("reissuable", sa.Boolean(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("type", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_service_tokens_name"), "service_tokens", ["name"], unique=False
    )
    op.add_column(
        "service_transactions",
        sa.Column(
            "currencies", postgresql.ARRAY(sa.String(length=64)), nullable=False
        ),
    )
    op.add_column(
        "service_transactions",
        sa.Column("height", sa.Integer(), nullable=False),
    )
    op.create_index(
        op.f("ix_service_transactions_currencies"),
        "service_transactions",
        ["currencies"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_service_transactions_currencies"),
        table_name="service_transactions",
    )
    op.drop_column("service_transactions", "height")
    op.drop_column("service_transactions", "currencies")
    op.drop_index(op.f("ix_service_tokens_name"), table_name="service_tokens")
    op.drop_table("service_tokens")
    # ### end Alembic commands ###
