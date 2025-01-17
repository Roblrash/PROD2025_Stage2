# auth.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

from solution.backend.db import get_db
from solution.models import Company
from solution.schemas import CompanyCreate, CompanyResponse
from solution.config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")

@router.post("/business/auth/sign-up", response_model=CompanyResponse)
async def sign_up(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    hashed_password = hash_password(company_data.password)
    new_company = Company(
        name=company_data.name,
        email=company_data.email,
        password=hashed_password,
    )
    db.add(new_company)

    try:
        await db.commit()
        await db.refresh(new_company)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")

    token = create_access_token(
        data={"sub": new_company.email, "company_id": new_company.id},
        expires_delta=timedelta(hours=1),
    )

    return CompanyResponse(token=token, company_id=new_company.id)