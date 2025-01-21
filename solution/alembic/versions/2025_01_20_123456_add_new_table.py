# alembic/versions/2025_01_20_123456_create_companies_and_promocodes.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = '2025_01_20_123456'
down_revision = None

def upgrade():
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('password', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'promo_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('limit', sa.Integer(), nullable=True, default=0),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('active_from', sa.Date(), nullable=True),
        sa.Column('active_until', sa.Date(), nullable=True),
        sa.Column('target', sa.JSON(), nullable=True),
        sa.Column('activations_count', sa.Integer(), nullable=True, default=0),
        sa.Column('mode', sa.String(15), nullable=False),
        sa.Column('promo_common', sa.String(30), nullable=True),
        sa.Column('promo_unique', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade():
    op.drop_table('promo_codes')
    op.drop_table('companies')