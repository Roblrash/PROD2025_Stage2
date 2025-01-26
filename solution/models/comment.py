from sqlalchemy import Column, DateTime, ForeignKey, Text, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db import Base
import uuid

class Commentary(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=False)
    text = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    author_id = Column(UUID(as_uuid=True), nullable=False)

    promo_code = relationship("PromoCode", back_populates="comments")
