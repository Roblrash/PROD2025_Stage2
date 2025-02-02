from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from src.backend.db import get_db
from src.schemas import UserRegister, SignIn, SignInResponse
from src.backend.config import settings
from src.models.user import User
from sqlalchemy.future import select
from redis.asyncio import Redis
import uuid
import logging

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

router = APIRouter(prefix="/api/user/auth")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
logging.basicConfig(level=logging.DEBUG)

TOKEN_TTL = 7200

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    for key, value in to_encode.items():
        if isinstance(value, uuid.UUID):
            to_encode[key] = str(value)

    return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")

async def save_token_to_redis(redis: Redis, user_id: uuid.UUID, token: str, ttl: int):
    key = f"user:{user_id}:token"
    await redis.set(key, token, ex=ttl)

async def invalidate_existing_token(redis: Redis, user_id: uuid.UUID):
    key = f"user:{user_id}:token"
    await redis.delete(key)

@router.post("/sign-up", response_model=SignInResponse)
async def register_user(
    user: UserRegister,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    existing_user = await db.execute(select(User).where(User.email == user.email))
    existing_user = existing_user.scalar()
    if existing_user:
        logging.error(f"User with email {user.email} already exists")
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed_password = hash_password(user.password)
    avatar_url = str(user.avatar_url) if user.avatar_url else None

    new_user = User(
        name=user.name,
        surname=user.surname,
        email=user.email,
        password=hashed_password,
        avatar_url=avatar_url,
        other=user.other.dict()
    )

    db.add(new_user)
    await db.commit()

    access_token = create_access_token({"user_id": new_user.id}, timedelta(seconds=TOKEN_TTL))

    await save_token_to_redis(redis, new_user.id, access_token, TOKEN_TTL)

    logging.info(f"User registered: {new_user.email}")

    return SignInResponse(token=access_token)

@router.post("/sign-in", response_model=SignInResponse)
async def sign_in(
    user: SignIn,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    result = await db.execute(select(User).where(User.email == user.email))
    user_db = result.scalar()

    if not user_db or not pwd_context.verify(user.password, user_db.password):
        logging.error(f"Invalid credentials for {user.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"user_id": user_db.id}, timedelta(seconds=TOKEN_TTL))

    await save_token_to_redis(redis, user_db.id, access_token, TOKEN_TTL)

    logging.info(f"User signed in: {user_db.email}")

    return SignInResponse(token=access_token)