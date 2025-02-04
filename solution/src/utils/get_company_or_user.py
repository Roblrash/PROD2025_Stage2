from fastapi.security import APIKeyHeader
from src.backend.config import settings
from src.models.user import User
from fastapi import HTTPException, Request, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError, ExpiredSignatureError
from src.backend.db import get_db
from src.models.company import Company
from sqlalchemy.future import select
from redis.asyncio import Redis
import uuid

auth_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

def extract_token(authorization: str) -> str:
    """
    Извлекает токен из заголовка Authorization.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid format")
    return authorization.split(" ")[1]

def decode_jwt_token(token: str) -> dict:
    """
    Декодирует JWT токен и обрабатывает возможные ошибки.
    """
    try:
        return jwt.decode(token, settings.RANDOM_SECRET, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def verify_token_in_redis(redis: Redis, key: str, token: str) -> None:
    """
    Проверяет наличие и соответствие токена в Redis.
    """
    stored_token = await redis.get(key)
    if not stored_token or stored_token.decode("utf-8") != token:
        raise HTTPException(status_code=401, detail="Token not found or mismatch in Redis")

async def get_current_user(
    authorization: str = Security(auth_header),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    token = extract_token(authorization)
    payload = decode_jwt_token(token)

    user_id_str = payload.get("user_id")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="Invalid token: 'user_id' not found")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user_id format")

    key = f"user:{user_id}:token"
    await verify_token_in_redis(redis, key, token)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_current_company(
    authorization: str = Security(auth_header),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> Company:
    token = extract_token(authorization)
    payload = decode_jwt_token(token)

    company_id = payload.get("company_id")
    if company_id is None:
        raise HTTPException(status_code=401, detail="Invalid token: 'company_id' not found")

    key = f"company:{company_id}:token"
    await verify_token_in_redis(redis, key, token)

    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar()
    if not company:
        raise HTTPException(status_code=401, detail="Company not found")
    return company
