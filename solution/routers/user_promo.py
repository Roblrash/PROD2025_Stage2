from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, Integer
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


from sqlalchemy.dialects.postgresql import JSONB

@router.get("/feed", response_model=List[PromoForUser])
async def get_promos(
        limit: int = Query(10, ge=1),
        offset: int = Query(0, ge=0),
        category: Optional[str] = Query(None),
        active: Optional[bool] = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    user_country = current_user.other.get("country")
    user_age = current_user.other.get("age")

    if not user_country or not user_age:
        raise HTTPException(status_code=400, detail="User country or age is missing")

    base_query = select(PromoCode)

    if category:
        base_query = base_query.filter(
            PromoCode.target["categories"].astext.cast(JSONB).contains([category])
        )

    if active is not None:
        base_query = base_query.filter(PromoCode.active == active)

    base_query = base_query.filter(
        or_(
            PromoCode.target["country"].astext == user_country,
            PromoCode.target["country"].is_(None)
        ),
        PromoCode.target["age_from"].astext.cast(Integer) <= user_age,
        or_(
            PromoCode.target["age_until"].is_(None),
            PromoCode.target["age_until"].astext.cast(Integer) >= user_age
        )
    )

    total_count_query = (
        select(func.count(PromoCode.id))
        .filter(*base_query._where_criteria)
    )

    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar() or 0

    final_query = (
        base_query.order_by(PromoCode.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(final_query)
    promos = result.scalars().all()

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
        promo_data = {
            key: uuid_to_str(value) for key, value in promo_data.items() if value is not None
        }

        response_data.append(promo_data)

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
