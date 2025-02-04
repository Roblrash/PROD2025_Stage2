import redis.asyncio as redis
from src.backend.config import settings
from redis.asyncio import Redis
from fastapi import Request

async def connect():
    return redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")

async def close(redis_client: redis.Redis):
    await redis_client.close()

def get_redis(request: Request) -> Redis:
    return request.app.state.redis