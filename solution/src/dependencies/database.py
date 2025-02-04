from redis.asyncio import Redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.db import async_session_maker

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

def get_redis(request: Request) -> Redis:
    return request.app.state.redis