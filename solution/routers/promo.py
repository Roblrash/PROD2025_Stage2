from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate, PromoReadOnly
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import class_mapper
from datetime import date
from sqlalchemy import func
from uuid import UUID

router = APIRouter(prefix="/api/business/promo")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo(
        promo_data: PromoCreate,
        db: AsyncSession = Depends(get_db),
        company=Depends(get_current_company),
) -> Dict[str, Any]:
    promo_code = promo_data.promo_common if promo_data.mode == 'COMMON' else None
    promo_codes = promo_data.promo_unique if promo_data.mode == 'UNIQUE' else None

    description = promo_data.description if promo_data.description else None

    try:
        active_from = datetime.strptime(promo_data.active_from, "%Y-%m-%d").date() if promo_data.active_from else None
        active_until = datetime.strptime(promo_data.active_until, "%Y-%m-%d").date() if promo_data.active_until else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format for 'active_from' or 'active_until'")

    new_promo = PromoCode(
        company_id=company.id,
        company_name=company.name,
        mode=promo_data.mode,
        promo_common=promo_code,
        promo_unique=promo_codes,
        limit=promo_data.max_count,
        max_count=promo_data.max_count,
        target=promo_data.target.dict() if promo_data.target else {},
        description=description,
        image_url=promo_data.image_url,
        active_from=active_from,
        active_until=active_until,
        active=True,
        activations_count=0,
        like_count=0,
        used_count=0
    )

    db.add(new_promo)
    await db.commit()
    await db.refresh(new_promo)

    return {"id": str(new_promo.id)}


from fastapi.responses import JSONResponse

def to_dict(obj):
    return {column.name: getattr(obj, column.name) for column in class_mapper(obj.__class__).columns}

def uuid_to_str(obj):
    if isinstance(obj, UUID):
        return str(obj)
    return obj

def remove_none_values(data):
    """Recursively remove None values from dictionaries and lists."""
    if isinstance(data, dict):
        return {k: remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    return data

@router.get("", response_model=List[PromoReadOnly])
async def get_promos(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query("active_from", regex="^(active_from|active_until)$"),
    country: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company),
):
    query = select(PromoCode).filter(PromoCode.company_id == company.id)

    if country:
        query = query.filter(PromoCode.target["country"].astext.in_(country))

    if sort_by == "active_from":
        query = query.order_by(PromoCode.active_from.desc())
    elif sort_by == "active_until":
        query = query.order_by(PromoCode.active_until.desc())
    else:
        query = query.order_by(PromoCode.id.desc())

    query_with_count = query.offset(offset).limit(limit)
    result = await db.execute(query_with_count)
    promos = result.scalars().all()

    total_count_result = await db.execute(
        select(func.count(PromoCode.id)).filter(PromoCode.company_id == company.id)
    )
    total_count = total_count_result.scalar() or 0

    validated_promos = []
    current_date = datetime.now().date()

    for promo in promos:
        active_from = promo.active_from or current_date
        active_until = promo.active_until or current_date
        mode = promo.mode or "COMMON"
        max_count = promo.max_count or 0
        used_count = promo.used_count or 0

        active_from_str = active_from.strftime("%Y-%m-%d") if isinstance(active_from, (datetime, date)) else None
        active_until_str = active_until.strftime("%Y-%m-%d") if isinstance(active_until, (datetime, date)) else None

        if active_from > current_date or active_until < current_date:
            promo.active = False
        elif mode == "COMMON" and used_count >= max_count:
            promo.active = False
        elif mode == "UNIQUE" and not promo.promo_unique:
            promo.active = False
        else:
            promo.active = True

        validated_promos.append(
            PromoReadOnly(
                **{**to_dict(promo),
                   'active_from': active_from_str,
                   'active_until': active_until_str}
            )
        )

    response_data = [
        {**promo.dict(by_alias=True),
         **({'active_from': active_from_str} if active_from_str else {}),
         **({'active_until': active_until_str} if active_until_str else {})}
        for promo in validated_promos
    ]

    response_data = [
        {key: uuid_to_str(value) for key, value in promo.items()}
        for promo in response_data
    ]

    response_data = remove_none_values(response_data)

    return JSONResponse(
        content=response_data,
        headers={"X-Total-Count": str(total_count)},
    )




