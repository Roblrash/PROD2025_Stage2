# alembic/versions/2025_01_20_123456_add_new_table.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2025_01_20_123456'
down_revision = None

def upgrade():
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password', sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'promo_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('code', sa.String(length=255), nullable=True),
        sa.Column('codes', sa.JSON(), nullable=True),
        sa.Column('limit', sa.Integer(), nullable=True, default=0),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('active_from', sa.Date(), nullable=True),
        sa.Column('active_until', sa.Date(), nullable=True),
        sa.Column('target', sa.JSON(), nullable=True),
        sa.Column('activations_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade():
    op.drop_table('promo_codes')

    op.drop_table('companies')
