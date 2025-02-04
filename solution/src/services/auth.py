from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.exc import IntegrityError
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.config import settings
from src.repositories.company import CompanyRepository
from fastapi import HTTPException

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.company_repo = CompanyRepository(db)

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        for key, value in to_encode.items():
            if isinstance(value, uuid.UUID):
                to_encode[key] = str(value)
        return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")

    async def save_token_to_redis(self, company_id: int, token: str, ttl: int):
        key = f"company:{company_id}:token"
        await self.redis.set(key, token, ex=ttl)

    async def invalidate_existing_token(self, company_id: int):
        key = f"company:{company_id}:token"
        await self.redis.delete(key)

    async def sign_up(self, company_data) -> dict:
        hashed_password = self.hash_password(company_data.password)
        company_dict = company_data.dict()
        company_dict["password"] = hashed_password

        try:
            new_company = await self.company_repo.create_company(company_dict)
        except (IntegrityError, ValueError):
            raise HTTPException(status_code=409, detail="Email is already registered")

        token = self.create_access_token(
            data={"sub": new_company.email, "company_id": new_company.id},
            expires_delta=timedelta(hours=2),
        )

        await self.save_token_to_redis(new_company.id, token, 7200)
        return {"token": token, "company_id": new_company.id}

    async def sign_in(self, email: str, password: str) -> dict:
        company = await self.company_repo.get_by_email(email)
        if not company or not pwd_context.verify(password, company.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        await self.invalidate_existing_token(company.id)
        token = self.create_access_token(
            data={"sub": company.email, "company_id": company.id},
            expires_delta=timedelta(hours=2),
        )
        await self.save_token_to_redis(company.id, token, 7200)
        return {"token": token}
