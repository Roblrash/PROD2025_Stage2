from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from backend.db import get_db
from routers.auth import get_current_company
from models.promocode import PromoCode
from schemas import PromoCreate

router = APIRouter(prefix="/api/business/promo")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_promo(
    promo_data: PromoCreate,
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company),
) -> Dict[str, Any]:
    new_promo = PromoCode(
        company_id=company.id,
        type=promo_data.type,
        code=promo_data.code,
        codes=promo_data.codes,
        limit=promo_data.limit,
        target=promo_data.target.dict(),
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