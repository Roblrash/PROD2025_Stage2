from src.backend.config import settings
from src.models.user import User
from src.routers.auth import auth_header
import logging
from fastapi import HTTPException, Request, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError, ExpiredSignatureError
from src.backend.db import get_db
from src.models.company import Company
from sqlalchemy.future import select
from typing import Optional
from redis.asyncio import Redis
import uuid

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

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
