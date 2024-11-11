"""Add timelock column to Output

Revision ID: 01b935993dac
Revises: 8b06e4540cd1
Create Date: 2024-10-20 13:38:54.939618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01b935993dac'
down_revision: Union[str, None] = '8b06e4540cd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('service_outputs', sa.Column('timelock', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('service_outputs', 'timelock')
    # ### end Alembic commands ###