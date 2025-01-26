from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '2025_01_20_123456'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создание таблицы пользователей
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('surname', sa.String(120), nullable=False),
        sa.Column('email', sa.String(120), unique=True, index=True, nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(350), nullable=True),
        sa.Column('other', sa.JSON, nullable=True)
    )

    # Создание таблицы компаний
    op.create_table(
        'companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(120), unique=True, index=True, nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
    )

    # Создание таблицы промокодов
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
        sa.Column('like_count', sa.Integer, default=0),
        sa.Column('used_count', sa.Integer, default=0),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('comment_count', sa.Integer, default=0)
    )

    # Создание таблицы активации промокодов пользователями
    op.create_table(
        'user_activated_promos',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('promo_id', UUID(as_uuid=True), sa.ForeignKey('promo_codes.promo_id', ondelete='CASCADE'), primary_key=True)
    )

    # Создание таблицы понравившихся промокодов пользователями
    op.create_table(
        'user_liked_promos',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('promo_id', UUID(as_uuid=True), sa.ForeignKey('promo_codes.promo_id', ondelete='CASCADE'), primary_key=True)
    )

    # Создание таблицы комментариев
    op.create_table(
        'comments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('text', sa.String(1000), nullable=False),
        sa.Column('date', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('author_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('promo_id', UUID(as_uuid=True), sa.ForeignKey('promo_codes.promo_id', ondelete='CASCADE'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['promo_id'], ['promo_codes.promo_id'], ondelete='CASCADE')
    )

def downgrade():
    # Удаление таблиц в случае отката миграции
    op.drop_table('comments')
    op.drop_table('user_activated_promos')
    op.drop_table('user_liked_promos')
    op.drop_table('users')
    op.drop_table('promo_codes')
    op.drop_table('companies')
