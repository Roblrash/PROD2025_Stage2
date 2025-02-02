from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, date
import aiohttp
from typing import List
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
import json
from src.backend.config import settings
from src.models.promocode import PromoCode
from src.models.user import User, user_activated_promos
from src.schemas import PromoForUser
from src.backend.db import get_db
from src.dependencies import get_current_user



"""
НЕ РЕАЛИЗОВАНАЯ РУЧКА "Код не работает :("
"""

router = APIRouter(prefix="/api/user")


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def is_currently_active(promo: PromoCode) -> bool:
    current_date = datetime.utcnow().date()
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max

    if not promo.active or not (active_from <= current_date <= active_until):
        return False

    if promo.mode == "COMMON" and promo.used_count >= promo.limit:
        return False

    if promo.mode == "UNIQUE" and promo.used_count >= promo.unique_count:
        return False

    return True


@router.get("/promo/history", response_model=List[PromoForUser])
async def get_promo_history(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_query = (
        select(User)
        .where(User.id == current_user.id)
        .options(
            selectinload(User.activated_promos),
            selectinload(User.liked_promos),
        )
    )
    user_result = await db.execute(user_query)
    user = user_result.scalar()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    activation_query = (
        select(user_activated_promos.c.promo_id, user_activated_promos.c.activation_count)
        .where(user_activated_promos.c.user_id == user.id)
        .order_by(user_activated_promos.c.activation_date.desc())
        .limit(limit)
        .offset(offset)
    )
    activation_result = await db.execute(activation_query)
    activated_promo_data = activation_result.fetchall()

    promo_history = []
    for promo_id, count in activated_promo_data:
        promo_query = select(PromoCode).where(PromoCode.promo_id == promo_id)
        promo_result = await db.execute(promo_query)
        promo = promo_result.scalar()

        if not promo:
            continue

        promo_history.extend([{
            "promo_id": str(promo.promo_id),
            "company_id": str(promo.company_id),
            "company_name": promo.company_name,
            "description": promo.description,
            "active": is_currently_active(promo),
            "is_activated_by_user": True,
            "like_count": promo.like_count,
            "is_liked_by_user": any(
                liked_promo.promo_id == promo.promo_id for liked_promo in user.liked_promos
            ),
            "comment_count": promo.comment_count,
            "image_url": promo.image_url or None,
        }] * count)

    return JSONResponse(content=promo_history, headers={"X-Total-Count": str(len(promo_history))})


async def call_antifraud_service(user_email: str, promo_id: UUID, redis: Redis) -> dict:
    cache_key = f"antifraud:{user_email}:{promo_id}"
    cached_result = await redis.get(cache_key)

    if cached_result:
        return json.loads(cached_result)

    antifraud_url = f"http://{settings.ANTIFRAUD_ADDRESS}/api/validate"
    payload = {"user_email": user_email, "promo_id": str(promo_id)}

    async with aiohttp.ClientSession() as session:
        for _ in range(2):
            async with session.post(antifraud_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    cache_duration = (datetime.fromisoformat(result.get("cache_until", "")) - datetime.utcnow()).total_seconds()
                    await redis.set(cache_key, json.dumps(result), ex=int(cache_duration))
                    return result

    raise HTTPException(status_code=403, detail="Ошибка антифрод-сервиса.")


@router.post("/promo/{id}/activate")
async def activate_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    user_query = select(User).where(User.id == current_user.id)
    user_result = await db.execute(user_query)
    user = user_result.scalar()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    promo_query = select(PromoCode).where(PromoCode.promo_id == id)
    promo_result = await db.execute(promo_query)
    promo = promo_result.scalar()

    if not promo or not is_currently_active(promo):
        raise HTTPException(status_code=403, detail="Промокод не активен или недоступен.")

    antifraud_result = await call_antifraud_service(current_user.email, id, redis)
    if not antifraud_result.get("ok", False):
        raise HTTPException(status_code=403, detail="Активировать промокод запрещено антифрод-сервисом.")

    activation_exists_query = select(user_activated_promos).where(
        user_activated_promos.c.user_id == user.id,
        user_activated_promos.c.promo_id == id,
    )
    activation_exists = (await db.execute(activation_exists_query)).scalar()

    if not activation_exists:
        await db.execute(user_activated_promos.insert().values(user_id=user.id, promo_id=id))
        promo.used_count += 1
        await db.commit()

    return {"promo": promo.promo_common if promo.mode == "COMMON" else promo.promo_unique[promo.used_count - 1]}