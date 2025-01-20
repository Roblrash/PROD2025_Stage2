from backend.db import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from models import *



class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    type = Column(String(10), nullable=False)
    code = Column(String(255), nullable=True)
    codes = Column(JSON, nullable=True)
    limit = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    active_from = Column(Date, nullable=True)
    active_until = Column(Date, nullable=True)
    target = Column(JSON, nullable=True)
    activations_count = Column(Integer, default=0)

    company = relationship("Company", back_populates="promos")