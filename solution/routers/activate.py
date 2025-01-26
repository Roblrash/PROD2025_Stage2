from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from datetime import datetime, date
import aiohttp
from typing import List
from config import settings
from models.promocode import PromoCode
from models.user import User, user_activated_promos
from schemas import PromoForUser
from backend.db import get_db
from routers.auth_user import get_current_user
from redis.asyncio import Redis
import json

router = APIRouter(prefix="/api/user")

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

@router.get("/promo/history", response_model=List[PromoForUser])
async def get_promo_history(
        limit: int = Query(10, ge=1),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    user_query = select(User).where(User.id == current_user.id)
    user_result = await db.execute(user_query)
    user = user_result.scalar()

    promo_query = select(PromoCode).join(user_activated_promos).where(
        user_activated_promos.c.user_id == user.id
    ).order_by(user_activated_promos.c.activation_date.desc()).limit(limit).offset(offset)

    promo_result = await db.execute(promo_query)
    promo_history = promo_result.scalars().all()

    return promo_history

async def call_antifraud_service(user_email: str, promo_id: UUID, redis: Redis) -> dict:
    cache_key = f"antifraud:{user_email}:{promo_id}"
    cached_result = await redis.get(cache_key)

    if cached_result:
        return json.loads(cached_result)

    antifraud_url = f"http://{settings.ANTIFRAUD_ADDRESS}/api/validate"
    payload = {"user_email": user_email, "promo_id": str(promo_id)}

    async with aiohttp.ClientSession() as session:
        for _ in range(2):
            async with session.post(antifraud_url, json=payload,
                                    headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    result = await response.json()
                    if "cache_until" in result:
                        cache_duration = (datetime.fromisoformat(result["cache_until"]) - datetime.utcnow()).total_seconds()
                        await redis.set(cache_key, json.dumps(result), ex=int(cache_duration))
                    return result

    raise HTTPException(status_code=403, detail="Ошибка антифрод-сервиса.")

@router.post("/promo/{id}/activate")
async def activate_promo(
        id: UUID = Path(...),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
        redis: Redis = Depends(get_redis)
):
    user_query = select(User).where(User.id == current_user.id)
    user_result = await db.execute(user_query)
    user = user_result.scalar()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    promo_query = select(PromoCode).where(PromoCode.promo_id == id)
    promo_result = await db.execute(promo_query)
    promo = promo_result.scalar()
    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден.")

    activation_query = select(user_activated_promos).where(
        user_activated_promos.c.user_id == user.id,
        user_activated_promos.c.promo_id == id,
    )
    activation_result = await db.execute(activation_query)
    activation_exists = activation_result.scalar()

    current_date = datetime.now().date()
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max

    if active_from > current_date or active_until < current_date:
        raise HTTPException(status_code=403, detail="Промокод не активен в текущий период.")

    if promo.target.get("country"):
        target_country = promo.target["country"].lower()
        user_country = user.other.get("country", "").lower()
        if target_country and target_country != user_country:
            raise HTTPException(status_code=403, detail="Промокод недоступен для вашей страны.")

    age_from = promo.target.get("age_from") or 0
    age_until = promo.target.get("age_until") or 1000
    user_age = user.other.get("age")
    if user_age is None or not (age_from <= user_age <= age_until):
        raise HTTPException(status_code=403, detail="Промокод недоступен для вашего возраста.")

    if promo.mode == "COMMON" and promo.used_count >= promo.max_count:
        raise HTTPException(status_code=403, detail="Лимит использования промокода исчерпан.")

    if promo.mode == "UNIQUE" and not promo.promo_unique:
        raise HTTPException(status_code=403, detail="Нет доступных уникальных промокодов.")

    antifraud_result = await call_antifraud_service(current_user.email, promo.promo_id, redis)
    if not antifraud_result.get("ok", False):
        raise HTTPException(status_code=403, detail="Активировать промокод запрещено антифрод-сервисом.")

    if not activation_exists:
        insert_stmt = user_activated_promos.insert().values(user_id=user.id, promo_id=id)
        await db.execute(insert_stmt)

    promo.used_count += 1
    if promo.mode == "UNIQUE":
        promo_value = promo.promo_unique.pop()
    else:
        promo_value = promo.promo_common

    await db.commit()

    return {"promo": promo_value}
