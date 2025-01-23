from backend.db import Base
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=func.now())
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    company_name = Column(String(50), nullable=False)
    promo_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)

    mode = Column(String(15), nullable=False)
    promo_common = Column(String(30), nullable=True)
    promo_unique = Column(JSON, nullable=True)

    description = Column(String(300), nullable=True)
    image_url = Column(String(350), nullable=True)
    active_from = Column(Date, nullable=True)
    active_until = Column(Date, nullable=True)

    target = Column(JSON, nullable=True)

    limit = Column(Integer, default=0)
    max_count = Column(Integer, nullable=True)
    activations_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    used_count = Column(Integer, default=0)

    active = Column(Boolean, default=True)

    company = relationship("Company", back_populates="promos")
