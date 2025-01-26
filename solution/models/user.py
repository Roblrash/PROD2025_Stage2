from sqlalchemy import Column, String, JSON, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from backend.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    avatar_url = Column(String(350), nullable=True)
    other = Column(JSON, nullable=True)

    activated_promos = relationship(
        "PromoCode", secondary="user_activated_promos", backref="users_activated"
    )
    liked_promos = relationship(
        "PromoCode", secondary="user_liked_promos", backref="users_liked"
    )

user_activated_promos = Table(
    'user_activated_promos',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('promo_id', UUID(as_uuid=True), ForeignKey('promo_codes.promo_id', ondelete="CASCADE"), primary_key=True)
)

user_liked_promos = Table(
    'user_liked_promos',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('promo_id', UUID(as_uuid=True), ForeignKey('promo_codes.promo_id', ondelete="CASCADE"), primary_key=True)
)
