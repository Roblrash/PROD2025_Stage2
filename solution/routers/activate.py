from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from datetime import datetime, date
import aiohttp
from config import settings
from models.promocode import PromoCode
from models.user import User
from backend.db import get_db
from routers.auth_user import get_current_user


router = APIRouter(prefix="/api/user")


@router.post("/promo/{id}/activate")
async def activate_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_query = select(User).where(User.email == current_user.email)
    user_result = await db.execute(user_query)
    user = user_result.scalar()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    user_country = user.other.get("country", "").lower()
    user_age = user.other.get("age")

    if not user_country or user_age is None:
        raise HTTPException(
            status_code=400,
            detail="У пользователя не указаны настройки страны или возраста.",
        )

    promo_query = select(PromoCode).where(PromoCode.promo_id == id)
    promo_result = await db.execute(promo_query)
    promo = promo_result.scalar()
    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден.")

    current_date = datetime.now().date()
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max

    if active_from > current_date or active_until < current_date:
        raise HTTPException(status_code=403, detail="Промокод не активен в текущий период.")

    target_country = promo.target.country
    if target_country and target_country.lower() != user_country:
        raise HTTPException(status_code=403, detail="Промокод недоступен для вашей страны.")

    age_from = promo.target.age_from or 0
    age_until = promo.target.age_until or 1000
    if not (age_from <= user_age <= age_until):
        raise HTTPException(status_code=403, detail="Промокод недоступен для вашего возраста.")

    if promo.mode == "COMMON" and promo.used_count >= promo.max_count:
        raise HTTPException(status_code=403, detail="Лимит использования промокода исчерпан.")

    if promo.mode == "UNIQUE" and not promo.promo_unique:
        raise HTTPException(status_code=403, detail="Нет доступных уникальных промокодов.")

    antifraud_result = await call_antifraud_service(current_user.email, promo.promo_id)
    if not antifraud_result["ok"]:
        raise HTTPException(status_code=403, detail="Активировать промокод запрещено антифрод-сервисом.")

    promo.used_count += 1
    if promo.mode == "UNIQUE":
        promo_value = promo.promo_unique.pop()
    else:
        promo_value = promo.promo_common

    await db.commit()

    return {"promo": promo_value}


async def call_antifraud_service(user_email: str, promo_id: str) -> dict:
    antifraud_url = f"{settings.ANTIFRAUD_ADDRESS}/api/validate"
    payload = {"user_email": user_email, "promo_id": promo_id}

    for _ in range(2):
        async with aiohttp.ClientSession() as session:
            async with session.post(antifraud_url, json=payload, headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    return await response.json()
    raise HTTPException(status_code=403, detail="Ошибка антифрод-сервиса.")