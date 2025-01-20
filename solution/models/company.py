from backend.db import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models import *

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password = Column(String(60), nullable=False)

    promos = relationship("PromoCode", back_populates="company")
