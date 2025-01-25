from fastapi import APIRouter, HTTPException, Depends, Security, Request
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from backend.db import get_db
from schemas import UserRegister, SignIn, SignInResponse
from config import settings
from models.user import User
from routers.auth import auth_header
from sqlalchemy.future import select
from redis.asyncio import Redis
import uuid
import logging

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

router = APIRouter(prefix="/user/auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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

async def get_current_user(
    authorization: str = Security(auth_header),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    logging.debug(f"Authorization header: {authorization}")

    if not authorization or not authorization.startswith("Bearer "):
        logging.error("Authorization header missing or invalid format")
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid format")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.RANDOM_SECRET, algorithms=["HS256"])
        user_id_str: str = payload.get("user_id")
        if user_id_str is None:
            logging.error("Invalid token: 'user_id' not found")
            raise HTTPException(status_code=401, detail="Invalid token: 'user_id' not found")

        user_id = uuid.UUID(user_id_str)
    except ExpiredSignatureError:
        logging.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logging.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    key = f"user:{user_id}:token"
    logging.debug(f"Redis key: {key}")

    stored_token = await redis.get(key)

    if not stored_token:
        logging.error(f"Token not found in Redis for key: {key}")
        raise HTTPException(status_code=401, detail="Token not found in Redis")

    if stored_token.decode("utf-8") != token:
        logging.error(f"Token mismatch: stored token {stored_token.decode('utf-8')} != provided token {token}")
        raise HTTPException(status_code=401, detail="Token mismatch or not valid")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if user is None:
        logging.error(f"User with ID {user_id} not found")
        raise HTTPException(status_code=401, detail="User not found")

    logging.debug(f"User found: {user}")

    return user

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