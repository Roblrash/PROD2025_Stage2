from sqlalchemy import Column, DateTime, ForeignKey, UUID, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db import Base
import uuid

class Commentary(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String(1000), nullable=False)
    date = Column(DateTime(timezone=True), default=func.now())
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.promo_id"), nullable=False)

    author = relationship("User", backref="comments")
    promo = relationship("PromoCode", back_populates="comments")
