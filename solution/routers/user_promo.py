from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, Integer, cast, and_, insert
from sqlalchemy.orm import class_mapper
from typing import List, Optional
from uuid import UUID
from backend.db import get_db
from routers.auth_user import get_current_user
from models.promocode import PromoCode
from models.user import User, user_activated_promos, user_liked_promos
from models.comment import Commentary
from schemas import  PromoForUser, Comment, CommentText, Author
from datetime import datetime
from starlette.responses import JSONResponse
from sqlalchemy.dialects.postgresql import JSONB

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
    query = select(User).where(User.id == user_id).join(user_activated_promos).filter(PromoCode.promo_id == promo_id)
    result = await db.execute(query)
    user = result.scalar()
    return user is not None

async def is_liked_by_user(user_id: UUID, promo_id: UUID, db: AsyncSession) -> bool:
    query = select(User).where(User.id == user_id).join(user_liked_promos).filter(PromoCode.promo_id == promo_id)
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
    user_country = (current_user.other.get("country") or "").lower()
    user_age = current_user.other.get("age") or 0

    print(f"User country: {user_country}")
    print(f"User age: {user_age}")
    print(f"Category filter: {category}")
    print(f"Active filter: {active}")

    base_query = select(PromoCode)

    if active is not None:
        base_query = base_query.filter(PromoCode.active == active)

    filter_condition_country = or_(
        func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country').is_(None),
        func.lower(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country')) == user_country
    )

    base_query = base_query.filter(filter_condition_country)

    filter_condition_age = and_(
        or_(
            func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_from').is_(None),
            func.cast(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_from'), Integer) <= user_age
        ),
        or_(
            func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_until').is_(None),
            func.cast(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_until'), Integer) >= user_age
        )
    )

    base_query = base_query.filter(filter_condition_age)

    if category:
        category = category.lower()

        filter_condition_category = and_(
            func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories').isnot(None),
            func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories').notin_([""])
        )

        filter_condition_category = and_(
            filter_condition_category,
            func.lower(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories')).contains(category)
        )

        base_query = base_query.filter(filter_condition_category)

    count_query = base_query.with_only_columns(func.count(PromoCode.id)).order_by(None)
    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar() or 0

    final_query = base_query.order_by(PromoCode.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(final_query)
    promos = result.scalars().all()

    response_data = []
    for promo in promos:
        promo_data = to_dict(promo)
        is_activated = await is_activated_by_user(current_user.id, promo.promo_id, db)
        is_liked = await is_liked_by_user(current_user.id, promo.promo_id, db)

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

    is_activated = await is_activated_by_user(current_user.id, promo.promo_id, db)
    is_liked = await is_liked_by_user(current_user.id, promo.promo_id, db)

    promo_data.update({
        "active": calculate_active(promo),
        "is_activated_by_user": is_activated,
        "is_liked_by_user": is_liked
    })

    promo_data = PromoForUser(**promo_data).dict(exclude_unset=True)

    response_data = {key: uuid_to_str(value) for key, value in promo_data.items() if value is not None}

    return JSONResponse(content=response_data)


@router.post("/promo/{id}/like")
async def like_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    promo_query = select(PromoCode).where(PromoCode.promo_id == id)
    promo_result = await db.execute(promo_query)
    promo = promo_result.scalar()

    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден")

    like_query = select(user_liked_promos).where(
        user_liked_promos.c.user_id == current_user.id,
        user_liked_promos.c.promo_id == id
    )
    like_result = await db.execute(like_query)
    like_exists = like_result.scalar()

    if like_exists:
        return JSONResponse(status_code=200, content={"status": "ok"})

    insert_stmt = user_liked_promos.insert().values(user_id=current_user.id, promo_id=id)
    await db.execute(insert_stmt)

    promo.like_count += 1
    db.add(promo)
    await db.commit()

    return JSONResponse(status_code=200, content={"status": "ok"})


@router.delete("/promo/{id}/like")
async def unlike_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    promo_query = select(PromoCode).where(PromoCode.promo_id == id)
    promo_result = await db.execute(promo_query)
    promo = promo_result.scalar()

    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден")

    like_query = select(user_liked_promos).where(
        user_liked_promos.c.user_id == current_user.id,
        user_liked_promos.c.promo_id == id
    )
    like_result = await db.execute(like_query)
    like_exists = like_result.scalar()

    if not like_exists:
        return JSONResponse(status_code=200, content={"status": "ok"})

    delete_stmt = user_liked_promos.delete().where(
        user_liked_promos.c.user_id == current_user.id,
        user_liked_promos.c.promo_id == id
    )
    await db.execute(delete_stmt)

    promo.like_count = max(0, promo.like_count - 1)
    db.add(promo)
    await db.commit()

    return JSONResponse(status_code=200, content={"status": "ok"})

@router.post("/promo/{id}/comments", response_model=Comment, status_code=201)
async def create_comment(
    id: UUID = Path(..., description="UUID промокода."),
    comment_data: CommentText = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    promo_query = await db.execute(select(PromoCode).where(PromoCode.promo_id == id))
    promo = promo_query.scalars().first()

    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден.")

    new_comment_id = UUID()
    new_comment = {
        "id": new_comment_id,
        "promo_id": id,
        "text": comment_data.text,
        "date": datetime.now().astimezone(),
        "author_id": current_user["id"],
    }

    stmt = insert(Commentary).values(new_comment)
    await db.execute(stmt)
    await db.commit()

    return Comment(
        id=new_comment_id,
        text=comment_data.text,
        date=new_comment["date"],
        author=Author(
            name=current_user["name"],
            surname=current_user["surname"],
            avatar_url=current_user.get("avatar_url"),
        ),
    )