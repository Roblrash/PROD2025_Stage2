from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate, PromoReadOnly, PromoPatch
from datetime import datetime
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from sqlalchemy.orm import class_mapper
from sqlalchemy.dialects.postgresql import JSONB
from datetime import date
from sqlalchemy import func, or_, cast
from uuid import UUID
import uuid

router = APIRouter(prefix="/api/business/promo")

from fastapi import HTTPException, status

def calculate_active(promo):
    current_date = datetime.now().date()
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max

    if active_from > current_date or active_until < current_date:
        return False
    if promo.mode == "COMMON" and promo.used_count >= promo.max_count:
        return False
    if promo.mode == "UNIQUE" and not promo.promo_unique:
        return False
    return True

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo(
    promo_data: PromoCreate,
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company),
) -> Dict[str, Any]:
    promo_code = promo_data.promo_common if promo_data.mode == "COMMON" else None
    promo_codes = promo_data.promo_unique if promo_data.mode == "UNIQUE" else None
    image_url = str(promo_data.image_url) if promo_data.image_url else None
    active_until = promo_data.active_until if promo_data.active_until else None
    active_from = promo_data.active_from if promo_data.active_from else None

    if active_from and active_until and active_from > active_until:
        raise HTTPException(
            status_code=400,
            detail="'active_from' cannot be later than 'active_until'."
        )

    promo_instance = PromoCode(
        company_id=company.id,
        company_name=company.name,
        mode=promo_data.mode,
        promo_common=promo_code,
        promo_unique=promo_codes,
        limit=promo_data.max_count,
        max_count=promo_data.max_count,
        target=promo_data.target.dict(),
        description=promo_data.description,
        image_url=image_url,
        active_from=active_from,
        active_until=active_until,
        active=True,
        like_count=0,
        used_count=0,
        created_at=func.now(),
        promo_id =uuid.uuid4(),
        comment_count=0
    )

    if not calculate_active(promo_instance):
        promo_instance.active = False

    db.add(promo_instance)
    await db.commit()
    await db.refresh(promo_instance)

    return {"id": str(promo_instance.promo_id)}



def to_dict(obj):
    return {column.name: getattr(obj, column.name) for column in class_mapper(obj.__class__).columns}

def uuid_to_str(obj):
    if isinstance(obj, UUID):
        return str(obj)
    return obj

def remove_none_values(data):
    if isinstance(data, dict):
        return {
            key: remove_none_values(value)
            for key, value in data.items()
            if value is not None
        }
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    else:
        return data

@router.get("", response_model=List[PromoReadOnly])
async def get_promos(
        limit: int = Query(10, ge=1),
        offset: int = Query(0, ge=0),
        sort_by: Optional[str] = Query(None, regex="^(active_from|active_until|id)$"),
        country: Optional[List[str]] = Query(None),
        db: AsyncSession = Depends(get_db),
        company=Depends(get_current_company),
):
    query = select(PromoCode).filter(PromoCode.company_id == company.id)

    if country:
        if isinstance(country, str):
            country = country.split(",")
        lower_country = [c.lower() for c in country]

        filter_condition = or_(
            func.jsonb_extract_path_text(
                cast(PromoCode.target, JSONB), 'country'
            ).is_(None),
            func.lower(
                func.jsonb_extract_path_text(
                    cast(PromoCode.target, JSONB), 'country'
                )
            ).in_(lower_country)
        )

        query = query.filter(filter_condition)

    total_count_query = select(func.count(PromoCode.id)).filter(PromoCode.company_id == company.id)

    if country:
        total_count_query = total_count_query.filter(filter_condition)

    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar() or 0

    if sort_by == "active_from":
        query = query.order_by(PromoCode.active_from.desc())
    elif sort_by == "active_until":
        query = query.order_by(PromoCode.active_until.desc())
    else:
        query = query.order_by(PromoCode.created_at.desc())

    query_with_count = query.offset(offset).limit(limit)
    result = await db.execute(query_with_count)
    promos = result.scalars().all()

    response_data = []
    for promo in promos:
        promo_data = to_dict(promo)

        target = promo_data.get("target", {})
        if isinstance(target, dict):
            promo_data["target"] = {key: value for key, value in target.items() if value is not None}

        if not promo_data["target"]:
            promo_data["target"] = {}

        promo_data.update({
            "active_from": promo.active_from.strftime("%Y-%m-%d") if promo.active_from else None,
            "active_until": promo.active_until.strftime("%Y-%m-%d") if promo.active_until else None,
            "active": calculate_active(promo),
        })

        promo_data = PromoReadOnly(**promo_data).dict(exclude_unset=True)

        response_data.append(promo_data)

    response_data = [
        {key: uuid_to_str(value) for key, value in promo.items() if value is not None}
        for promo in response_data
    ]

    return JSONResponse(
        content=response_data,
        headers={"X-Total-Count": str(total_count)},
    )


async def get_promo_and_check_company(
        id: UUID, company_id: UUID, db: AsyncSession
) -> PromoCode:
    query = select(PromoCode).where(PromoCode.promo_id == id)
    result = await db.execute(query)
    promo = result.scalar()

    if promo is None:
        raise HTTPException(status_code=404, detail="Промокод не найден")

    if promo.company_id != company_id:
        raise HTTPException(status_code=403, detail="Промокод не принадлежит этой компании.")

    return promo


@router.get("/{id}", response_model=PromoReadOnly)
async def get_promo_by_id(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company),
):
    promo = await get_promo_and_check_company(id, company.id, db)

    promo_data = to_dict(promo)

    target = promo_data.get("target", {})
    if isinstance(target, dict):
        promo_data["target"] = {key: value for key, value in target.items() if value is not None}

    if not promo_data["target"]:
        promo_data["target"] = {}

    promo_data.update({
        "active_from": promo.active_from.strftime("%Y-%m-%d") if promo.active_from else None,
        "active_until": promo.active_until.strftime("%Y-%m-%d") if promo.active_until else None,
        "active": calculate_active(promo),
    })

    promo_data = PromoReadOnly(**promo_data).dict(exclude_unset=True)

    response_data = {key: uuid_to_str(value) for key, value in promo_data.items() if value is not None}

    return JSONResponse(content=response_data)


@router.patch("/{id}", status_code=status.HTTP_200_OK)
async def patch_promo(
    promo_data: PromoPatch,
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company),
):
    promo = await get_promo_and_check_company(id, company.id, db)

    if promo.mode == "UNIQUE":
        if promo_data.max_count is not None and promo_data.max_count != 1:
            raise HTTPException(
                status_code=400,
                detail="Field 'max_count' must be 1 when mode is 'UNIQUE'."
            )

    if promo.mode == "COMMON" and promo_data.max_count is not None:
        if promo_data.max_count < promo.used_count:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Field 'max_count' cannot be less "
                    "than the current number of activations (used_count)."
                )
            )

        promo.max_count = promo_data.max_count

    if promo_data.description:
        promo.description = promo_data.description
    if promo_data.image_url:
        promo.image_url = str(promo_data.image_url)
    if promo_data.target:
        promo.target = promo_data.target.dict()

    if promo_data.active_from and promo_data.active_until:
        if promo_data.active_from > promo_data.active_until:
            raise HTTPException(
                status_code=400,
                detail="'active_from' cannot be later than 'active_until'."
            )

    if promo_data.active_from:
        promo.active_from = promo_data.active_from
    if promo_data.active_until:
        promo.active_until = promo_data.active_until

    promo.active = calculate_active(promo)

    db.add(promo)
    await db.commit()
    await db.refresh(promo)

    promo_data = to_dict(promo)
    target = promo_data.get("target", {})
    if isinstance(target, dict):
        promo_data["target"] = {key: value for key, value in target.items() if value is not None}
    if not promo_data["target"]:
        promo_data["target"] = {}

    promo_data.update({
        "active_from": promo.active_from.strftime("%Y-%m-%d") if promo.active_from else None,
        "active_until": promo.active_until.strftime("%Y-%m-%d") if promo.active_until else None,
        "active": promo.active,
    })

    promo_data = PromoReadOnly(**promo_data).dict(exclude_unset=True)
    response_data = {key: uuid_to_str(value) for key, value in promo_data.items() if value is not None}

    return JSONResponse(content=response_data)

