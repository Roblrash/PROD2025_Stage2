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

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi.responses import JSONResponse


def is_currently_active(promo: PromoCode) -> bool:
    current_date = datetime.utcnow().date()

    if not promo.active:
        return False
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max
    if not (active_from <= current_date <= active_until):
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

    if user is None:
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

    formatted_promo_history = []
    for promo_id, count in activated_promo_data:
        promo_query = select(PromoCode).where(PromoCode.promo_id == promo_id)
        promo_result = await db.execute(promo_query)
        promo = promo_result.scalar()

        if promo is None:
            continue

        is_active = is_currently_active(promo)

        is_activated_by_user = True
        is_liked_by_user = any(
            liked_promo.promo_id == promo.promo_id for liked_promo in user.liked_promos
        )

        formatted_promo = {
            "promo_id": str(promo.promo_id),
            "company_id": str(promo.company_id),
            "company_name": promo.company_name,
            "description": promo.description,
            "active": is_active,
            "is_activated_by_user": is_activated_by_user,
            "like_count": promo.like_count,
            "is_liked_by_user": is_liked_by_user,
            "comment_count": promo.comment_count,
        }

        if promo.image_url:
            formatted_promo["image_url"] = promo.image_url

        formatted_promo_history.extend([formatted_promo] * count)

    return JSONResponse(content=formatted_promo_history, headers={"X-Total-Count": str(len(formatted_promo_history))})


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
    # Проверка пользователя
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

    if promo.mode == "UNIQUE":
        if promo.used_count >= promo.unique_count:
            raise HTTPException(status_code=403, detail="Все уникальные коды уже активированы.")

        unique_index = promo.used_count
        unique_code = promo.promo_unique[unique_index]

        promo.used_count += 1
        await db.merge(promo)

    elif promo.mode == "COMMON":
        if promo.used_count >= promo.limit:
            raise HTTPException(status_code=403, detail="Лимит активаций достигнут.")
        unique_code = promo.promo_common
        promo.used_count += 1
        await db.merge(promo)

    if not activation_exists:
        insert_stmt = user_activated_promos.insert().values(user_id=user.id, promo_id=id, activation_count=1)
        await db.execute(insert_stmt)
    else:
        update_stmt = (
            user_activated_promos.update()
            .where(user_activated_promos.c.user_id == user.id)
            .where(user_activated_promos.c.promo_id == id)
            .values(activation_count=user_activated_promos.c.activation_count + 1)
        )
        await db.execute(update_stmt)

    await db.commit()

    return {"promo": unique_code}

