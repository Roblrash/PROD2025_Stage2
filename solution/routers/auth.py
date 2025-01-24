from fastapi import APIRouter, HTTPException, Depends, Request, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from typing import Dict
from fastapi.security import APIKeyHeader
from datetime import datetime, timedelta
from backend.db import get_db
from models.company import Company
from schemas import CompanyResponse, CompanyCreate, SignIn, SignInResponse, CompanyId
from config import settings
from sqlalchemy.future import select
from redis.asyncio import Redis
import uuid
from typing import Optional


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


router = APIRouter(prefix="/api")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})

    for key, value in to_encode.items():
        if isinstance(value, uuid.UUID):
            to_encode[key] = str(value)

    return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")


async def save_token_to_redis(redis: Redis, company_id: int, token: str, ttl: int):
    key = f"company:{company_id}:token"
    await redis.set(key, token, ex=ttl)


async def invalidate_existing_token(redis: Redis, company_id: int):
    key = f"company:{company_id}:token"
    await redis.delete(key)


auth_header = APIKeyHeader(name="Authorization", auto_error=False)

import logging

logging.basicConfig(level=logging.DEBUG)

async def get_current_company(
        authorization: str = Security(auth_header),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
) -> Company:
    logging.debug(f"Authorization header: {authorization}")

    if not authorization or not authorization.startswith("Bearer "):
        logging.error("Authorization header missing or invalid format")
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid format")

    token = authorization.split(" ")[1]

    logging.debug(f"Decoded token: {token}")

    try:
        payload = jwt.decode(token, settings.RANDOM_SECRET, algorithms=["HS256"])
        company_id: Optional[int] = payload.get("company_id")
        if company_id is None:
            logging.error("Invalid token: 'company_id' not found")
            raise HTTPException(status_code=401, detail="Invalid token: 'company_id' not found")
    except ExpiredSignatureError:
        logging.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logging.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    key = f"company:{company_id}:token"
    logging.debug(f"Redis key: {key}")

    stored_token = await redis.get(key)

    if not stored_token:
        logging.error(f"Token not found in Redis for key: {key}")
        raise HTTPException(status_code=401, detail="Token not found in Redis")

    if stored_token.decode("utf-8") != token:
        logging.error(f"Token mismatch: stored token {stored_token.decode('utf-8')} != provided token {token}")
        raise HTTPException(status_code=401, detail="Token mismatch or not valid")

    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar()

    if company is None:
        logging.error(f"Company with ID {company_id} not found")
        raise HTTPException(status_code=401, detail="Company not found")

    logging.debug(f"Company found: {company}")

    return company



@router.post("/business/auth/sign-up", response_model=CompanyResponse)
async def sign_up(
        company_data: CompanyCreate,
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
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
        expires_delta=timedelta(hours=2),
    )

    await save_token_to_redis(redis, new_company.id, token, ttl=7200)

    return CompanyResponse(token=token, company_id=CompanyId(company_id=new_company.id))


@router.post("/business/auth/sign-in", response_model=SignInResponse)
async def sign_in(
        sign_in_data: SignIn,
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    result = await db.execute(select(Company).where(Company.email == sign_in_data.email))
    company = result.scalar()

    if not company or not pwd_context.verify(sign_in_data.password, company.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await invalidate_existing_token(redis, company.id)

    token = create_access_token(
        data={"sub": company.email, "company_id": company.id},
        expires_delta=timedelta(hours=2),
    )

    await save_token_to_redis(redis, company.id, token, ttl=7200)

    return SignInResponse(token=token)