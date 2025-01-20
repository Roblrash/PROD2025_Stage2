from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate

router = APIRouter(prefix="/api/business/promo")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo(
        promo_data: PromoCreate,
        db: AsyncSession = Depends(get_db),
        company=Depends(get_current_company),
) -> Dict[str, Any]:
    promo_common = promo_data.promo_common if promo_data.promo_common is not None else None
    promo_unique = promo_data.promo_unique if promo_data.promo_unique is not None else None

    new_promo = PromoCode(
        company_id=company.id,
        type=promo_data.mode,
        code=promo_common,
        codes=promo_unique,
        limit=promo_data.max_count,
        target=promo_data.target.dict() if promo_data.target else {},  # Если target не указан, пустой словарь
        description=promo_data.description,
        active_from=promo_data.active_from,
        active_until=promo_data.active_until,
        active=True,
        activations_count=0,
    )

    db.add(new_promo)
    await db.commit()
    await db.refresh(new_promo)

    return {"id": str(new_promo.id)}
