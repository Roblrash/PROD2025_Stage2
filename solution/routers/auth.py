from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt
from solution.models.company import Company
from solution.schemas import CompanyNameCreate, Email, Password
from solution.backend.db import async_session_maker
from datetime import datetime, timedelta
import jwt
import os


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=2)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("RANDOM_SECRET"), algorithm="HS256")
    return encoded_jwt


async def register_company(db: AsyncSession, name: CompanyNameCreate, email: Email, password: Password):
    result = await db.execute(select(Company).filter(Company.email == email.email))
    company_in_db = result.scalars().first()

    if company_in_db:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    if len(name.name) < 1 or len(name.name) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid company name")

    hashed_password = bcrypt.hashpw(password.password.encode('utf-8'), bcrypt.gensalt())

    new_company = Company(name=name.name, email=email.email, password_hash=hashed_password)
    db.add(new_company)
    await db.commit()

    access_token = create_access_token(data={"sub": new_company.email, "id": new_company.id})

    return {"token": access_token, "company_id": new_company.id}
