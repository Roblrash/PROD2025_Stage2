from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '2025_01_20_123456'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создание таблицы companies
    op.create_table(
        'companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(120), unique=True, index=True, nullable=False),
        sa.Column('password', sa.String(60), nullable=False),
    )

    # Создание таблицы promo_codes
    op.create_table(
        'promo_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('company_name', sa.String(50), nullable=False),
        sa.Column('promo_id', UUID(as_uuid=True), unique=True, default=uuid.uuid4),
        sa.Column('mode', sa.String(15), nullable=False),
        sa.Column('promo_common', sa.String(30), nullable=True),
        sa.Column('promo_unique', sa.JSON, nullable=True),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('image_url', sa.String(350), nullable=True),
        sa.Column('active_from', sa.Date, nullable=True),
        sa.Column('active_until', sa.Date, nullable=True),
        sa.Column('target', sa.JSON, nullable=True),
        sa.Column('limit', sa.Integer, default=0),
        sa.Column('max_count', sa.Integer, nullable=True),
        sa.Column('activations_count', sa.Integer, default=0),
        sa.Column('like_count', sa.Integer, default=0),
        sa.Column('used_count', sa.Integer, default=0),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now())
    )


def downgrade():
    # Удаление таблиц
    op.drop_table('promo_codes')
    op.drop_table('companies')
