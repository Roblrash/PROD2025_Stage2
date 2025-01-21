from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate, PromoReadOnly
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import func

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
        mode=promo_data.mode,
        promo_common=promo_code,
        promo_unique=promo_codes,
        limit=promo_data.max_count,
        target=promo_data.target.dict() if promo_data.target else {},
        description=description,
        active_from=active_from,
        active_until=active_until,
        active=True,
        activations_count=0,
    )

    db.add(new_promo)
    await db.commit()
    await db.refresh(new_promo)

    return {"id": str(new_promo.id)}


@router.get("", response_model=List[PromoReadOnly])
async def get_promos(
        limit: int = Query(10, ge=1),
        offset: int = Query(0, ge=0),
        sort_by: Optional[str] = Query("active_from", regex="^(active_from|active_until)$"),
        country: Optional[List[str]] = Query(None),
        db: AsyncSession = Depends(get_db),
        company=Depends(get_current_company),
) -> List[PromoReadOnly]:
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

    total_count_result = await db.execute(select(func.count(PromoCode.id)).filter(PromoCode.company_id == company.id))
    total_count = total_count_result.scalar()

    headers = {"X-Total-Count": str(total_count)}

    return promos if promos else [], headers

