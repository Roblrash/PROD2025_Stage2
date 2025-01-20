from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate

router = APIRouter(prefix="/api/business/promo")


from datetime import datetime


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo(
        promo_data: PromoCreate,
        db: AsyncSession = Depends(get_db),
        company=Depends(get_current_company),
) -> Dict[str, Any]:
    promo_code = promo_data.promo_common if promo_data.mode == 'COMMON' else None
    promo_codes = promo_data.promo_unique if promo_data.mode == 'UNIQUE' else None

    description = promo_data.description if promo_data.description else None

    active_from = datetime.strptime(promo_data.active_from, "%Y-%m-%d").date() if promo_data.active_from else None
    active_until = datetime.strptime(promo_data.active_until, "%Y-%m-%d").date() if promo_data.active_until else None

    new_promo = PromoCode(
        company_id=company.id,
        type=promo_data.mode,
        code=promo_code,
        codes=promo_codes,
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
