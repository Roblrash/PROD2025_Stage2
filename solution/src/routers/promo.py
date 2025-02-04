from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi.responses import JSONResponse
from src.backend.db import get_db
from src.schemas.promo import PromoCreate, PromoReadOnly, PromoPatch, PromoStat
from src.services.promo import PromoService
from src.utils.get_company_or_user import get_current_company
from fastapi.encoders import jsonable_encoder


router = APIRouter(prefix="/api/business/promo")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo(
    promo_data: PromoCreate,
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company)
) -> Dict[str, Any]:
    service = PromoService(db)
    result = await service.create_promo(promo_data, company)
    return result

@router.get("", response_model=List[PromoReadOnly])
async def get_promos(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None, regex="^(active_from|active_until|id)$"),
    country: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company)
):
    service = PromoService(db)
    promos, total = await service.get_promos(company, limit, offset, sort_by, country)
    json_compatible_data = jsonable_encoder(promos)
    return JSONResponse(content=json_compatible_data, headers={"X-Total-Count": str(total)})

@router.get("/{id}", response_model=PromoReadOnly)
async def get_promo_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company)
):
    service = PromoService(db)
    try:
        promo = await service.get_promo_by_id(id, company.id)
        json_compatible_data = jsonable_encoder(promo)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JSONResponse(content=json_compatible_data)


@router.patch("/{id}", status_code=status.HTTP_200_OK)
async def patch_promo(
    promo_data: PromoPatch,
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company)
):
    service = PromoService(db)
    try:
        updated = await service.patch_promo(id, promo_data, company.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content=updated)

@router.get("/{id}/stat", response_model=PromoStat)
async def get_promo_stat(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    company=Depends(get_current_company)
):
    service = PromoService(db)
    try:
        stat = await service.get_promo_stat(id, company.id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return stat
