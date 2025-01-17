"""Initial migration

Revision ID: 22ab310ba27a
Revises: 35360ae4cea8
Create Date: 2025-01-17 22:26:38.945126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22ab310ba27a'
down_revision: Union[str, None] = '35360ae4cea8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('companies', sa.Column('password', sa.String(length=128), nullable=False))
    op.drop_index('ix_companies_name', table_name='companies')
    op.drop_column('companies', 'password_hash')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('companies', sa.Column('password_hash', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.create_index('ix_companies_name', 'companies', ['name'], unique=True)
    op.drop_column('companies', 'password')
    # ### end Alembic commands ###
