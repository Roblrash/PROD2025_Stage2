from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import re
from backend.db import get_db
from models import Company
from schemas import CompanyCreate, CompanyResponse, SignInRequest, SignInResponse
from config import settings
from sqlalchemy.future import select
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


router = APIRouter(prefix="/api")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/business/auth/sign-in")


def validate_password(password: str) -> bool:
    if not re.search(r'[A-Z]', password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы одну заглавную букву")

    if not re.search(r'[a-z]', password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы одну строчную букву")

    if not re.search(r'[0-9]', password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы одну цифру")

    if not re.search(r'[@#$%^&+=!]', password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы один специальный символ (@, #, $, %, ^, &, +, =, !)")

    return True


def hash_password(password: str) -> str:
    validate_password(password)
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")


async def save_token_to_redis(redis: Redis, company_id: int, token: str, ttl: int):
    key = f"company:{company_id}:token"
    await redis.set(key, token, ex=ttl)


async def invalidate_existing_token(redis: Redis, company_id: int):
    key = f"company:{company_id}:token"
    await redis.delete(key)


async def get_current_company(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    try:
        payload = jwt.decode(token, settings.RANDOM_SECRET, algorithms=["HS256"])
        company_id: int = payload.get("company_id")
        if company_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    key = f"company:{company_id}:token"
    stored_token = await redis.get(key)

    if stored_token is None:
        raise HTTPException(status_code=401, detail="Token is no longer valid")

    if stored_token.decode("utf-8") != token:
        raise HTTPException(status_code=401, detail="Token mismatch")

    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar()

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

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

    return CompanyResponse(token=token, company_id=new_company.id)


@router.post("/business/auth/sign-in", response_model=SignInResponse)
async def sign_in(
    sign_in_data: SignInRequest,
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

    return SignInResponse(token=token, company_id=company.id)
