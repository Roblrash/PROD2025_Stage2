import aioredis
from config import settings

# Инициализация Redis клиента
async def connect():
    return await aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")

# Функция для закрытия соединения с Redis
async def close(redis):
    await redis.close()
