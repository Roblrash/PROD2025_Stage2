from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import class_mapper
from typing import List, Optional
from uuid import UUID
from backend.db import get_db
from routers.auth_user import get_current_user
from models.promocode import PromoCode
from models.user import User, user_activated_promos, user_liked_promos
from schemas import  PromoForUser
from datetime import datetime
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/user")

def calculate_active(promo):
    current_date = datetime.now().date()
    active_from = promo.active_from or datetime.min.date()
    active_until = promo.active_until or datetime.max.date()

    if active_from > current_date or active_until < current_date:
        return False
    if promo.mode == "COMMON" and promo.used_count >= promo.max_count:
        return False
    if promo.mode == "UNIQUE" and not promo.promo_unique:
        return False
    return True

def to_dict(obj):
    return {column.name: getattr(obj, column.name) for column in class_mapper(obj.__class__).columns}

def uuid_to_str(obj):
    if isinstance(obj, UUID):
        return str(obj)
    return obj

async def is_activated_by_user(user_id: UUID, promo_id: UUID, db: AsyncSession) -> bool:
    query = select(User).where(User.id == user_id).join(user_activated_promos).filter(PromoCode.id == promo_id)
    result = await db.execute(query)
    user = result.scalar()
    return user is not None

async def is_liked_by_user(user_id: UUID, promo_id: UUID, db: AsyncSession) -> bool:
    query = select(User).where(User.id == user_id).join(user_liked_promos).filter(PromoCode.id == promo_id)
    result = await db.execute(query)
    user = result.scalar()
    return user is not None

@router.get("/feed", response_model=List[PromoForUser])
async def get_promos(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = select(PromoCode)

    if category:
        query = query.filter(PromoCode.category.contains([category]))

    if active is not None:
        query = query.filter(PromoCode.active == active)

    query = query.order_by(PromoCode.created_at.desc())

    query_with_count = query.offset(offset).limit(limit)
    result = await db.execute(query_with_count)
    promos = result.scalars().all()

    total_count_result = await db.execute(select(func.count(PromoCode.id)))
    total_count = total_count_result.scalar() or 0

    response_data = []
    for promo in promos:
        promo_data = to_dict(promo)

        is_activated = await is_activated_by_user(current_user.id, promo.id, db)
        is_liked = await is_liked_by_user(current_user.id, promo.id, db)

        promo_data.update({
            "active": calculate_active(promo),
            "is_activated_by_user": is_activated,
            "is_liked_by_user": is_liked
        })

        promo_data = PromoForUser(**promo_data).dict(exclude_unset=True)

        response_data.append(promo_data)

    response_data = [
        {key: uuid_to_str(value) for key, value in promo.items() if value is not None}
        for promo in response_data
    ]

    return JSONResponse(
        content=response_data,
        headers={"X-Total-Count": str(total_count)}
    )

@router.get("/promo/{id}", response_model=PromoForUser)
async def get_promo_by_id(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(PromoCode).where(PromoCode.promo_id == id)
    result = await db.execute(query)
    promo = result.scalar()

    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден")

    promo_data = to_dict(promo)

    is_activated = await is_activated_by_user(current_user.id, promo.id, db)
    is_liked = await is_liked_by_user(current_user.id, promo.id, db)

    promo_data.update({
        "active": calculate_active(promo),
        "is_activated_by_user": is_activated,
        "is_liked_by_user": is_liked
    })

    promo_data = PromoForUser(**promo_data).dict(exclude_unset=True)

    response_data = {key: uuid_to_str(value) for key, value in promo_data.items() if value is not None}

    return JSONResponse(content=response_data)
