import redis.asyncio as redis
from config import settings

async def connect():
    return redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")

async def close(redis_client):
    await redis_client.close()
