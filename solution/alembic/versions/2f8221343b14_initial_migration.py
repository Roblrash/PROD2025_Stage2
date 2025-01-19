"""Initial migration

Revision ID: 2f8221343b14
Revises: 22ab310ba27a
Create Date: 2025-01-19 22:31:54.917852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f8221343b14'
down_revision: Union[str, None] = '22ab310ba27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('promo_codes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=10), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.Column('activations_limit', sa.Integer(), nullable=True),
    sa.Column('activations_count', sa.Integer(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('target', sa.JSON(), nullable=True),
    sa.Column('unique_values', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('promo_codes')
    # ### end Alembic commands ###
