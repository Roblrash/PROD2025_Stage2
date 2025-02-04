import uuid
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.backend.config import settings
from src.repositories.user import UserRepository

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
TOKEN_TTL = 7200


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.user_repo = UserRepository(db)
        self.redis = redis

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        for key, value in to_encode.items():
            if isinstance(value, uuid.UUID):
                to_encode[key] = str(value)
        return jwt.encode(to_encode, settings.RANDOM_SECRET, algorithm="HS256")

    async def save_token_to_redis(self, user_id: uuid.UUID, token: str):
        key = f"user:{user_id}:token"
        await self.redis.set(key, token, ex=TOKEN_TTL)

    async def invalidate_existing_token(self, user_id: uuid.UUID):
        key = f"user:{user_id}:token"
        await self.redis.delete(key)

    async def register_user(self, user_data) -> dict:
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already registered")

        hashed_password = self.hash_password(user_data.password)
        user_dict = user_data.dict()
        user_dict["password"] = hashed_password

        try:
            new_user = await self.user_repo.create_user(user_dict)
        except ValueError as e:
            raise HTTPException(status_code=409, detail="Email already registered") from e

        access_token = self.create_access_token({"user_id": new_user.id}, timedelta(seconds=TOKEN_TTL))
        await self.save_token_to_redis(new_user.id, access_token)
        return {"token": access_token}

    async def sign_in(self, email: str, password: str) -> dict:
        user_db = await self.user_repo.get_by_email(email)
        if not user_db or not self.verify_password(password, user_db.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = self.create_access_token({"user_id": user_db.id}, timedelta(seconds=TOKEN_TTL))
        await self.save_token_to_redis(user_db.id, access_token)
        return {"token": access_token}
