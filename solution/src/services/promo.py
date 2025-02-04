from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.promo import PromoRepository
from src.models.promocode import PromoCode
from src.schemas.promo import PromoCreate, PromoPatch, PromoReadOnly, PromoStat, CountryStat
from src.utils.promo_helpers import calculate_active
from src.utils.serializer import to_dict, uuid_to_str

class PromoService:
    def __init__(self, db: AsyncSession):
        self.repo = PromoRepository(db)

    async def create_promo(self, promo_data: PromoCreate, company) -> dict:
        active_from = promo_data.active_from
        active_until = promo_data.active_until
        if active_from and active_until and active_from > active_until:
            raise HTTPException(status_code=400, detail="'active_from' cannot be later than 'active_until'.")

        promo_code = promo_data.promo_common if promo_data.mode == "COMMON" else None
        promo_codes = promo_data.promo_unique if promo_data.mode == "UNIQUE" else None
        image_url = str(promo_data.image_url) if promo_data.image_url else None
        unique_count = len(promo_codes) if promo_codes else 0

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
            created_at=datetime.utcnow(),
            promo_id=uuid4(),
            comment_count=0,
            unique_count=unique_count
        )

        if not calculate_active(promo_instance):
            promo_instance.active = False

        promo = await self.repo.create_promo(promo_instance)
        return {"id": str(promo.promo_id)}

    async def get_promos(self, company, limit: int, offset: int, sort_by: Optional[str], country: Optional[list]) -> (list, int):
        filter_condition = None
        if country:
            lower_country = [c.lower() for c in country]
            from sqlalchemy import or_, func, cast
            from sqlalchemy.dialects.postgresql import JSONB
            filter_condition = or_(
                func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country').is_(None),
                func.lower(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country')).in_(lower_country)
            )

        promos = await self.repo.get_promos_by_company(company.id, filter_condition, offset, limit, sort_by)
        total = await self.repo.count_promos_by_company(company.id, filter_condition)
        result = []
        for promo in promos:
            promo_dict = to_dict(promo)
            target = promo_dict.get("target", {})
            if isinstance(target, dict):
                promo_dict["target"] = {k: v for k, v in target.items() if v is not None}
            if not promo_dict["target"]:
                promo_dict["target"] = {}
            promo_dict.update({
                "active_from": promo.active_from.strftime("%Y-%m-%d") if promo.active_from else None,
                "active_until": promo.active_until.strftime("%Y-%m-%d") if promo.active_until else None,
                "active": calculate_active(promo),
            })
            promo_ro = PromoReadOnly(**promo_dict).dict(exclude_unset=True)
            result.append(promo_ro)
        result = [{k: uuid_to_str(v) for k, v in promo.items() if v is not None} for promo in result]
        return result, total

    async def get_promo_by_id(self, promo_id: UUID, company_id: UUID) -> PromoReadOnly:
        promo = await self.repo.get_promo_by_id(promo_id)

        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден")
        if promo.company_id != company_id:
            raise HTTPException(status_code=403, detail="Промокод не принадлежит этой компании.")

        return TypeAdapter(PromoReadOnly).validate_python(promo)

    async def patch_promo(self, promo_id: UUID, promo_data: PromoPatch, company_id: UUID) -> PromoReadOnly:
        promo = await self.repo.get_promo_by_id(promo_id)
        if not promo or promo.company_id != company_id:
            raise HTTPException(status_code=404, detail="Промокод не найден")

        if promo.mode == "UNIQUE" and promo_data.max_count not in (None, 1):
            raise HTTPException(status_code=400, detail="Для UNIQUE промокода max_count должен быть 1")

        if promo.mode == "COMMON" and promo_data.max_count is not None:
            if promo_data.max_count < promo.used_count:
                raise HTTPException(
                    status_code=400,
                    detail="Максимальное количество не может быть меньше использованного"
                )

        update_data = promo_data.dict(exclude_unset=True)

        if 'active_from' in update_data or 'active_until' in update_data:
            active_from = update_data.get('active_from', promo.active_from)
            active_until = update_data.get('active_until', promo.active_until)

            if active_from and active_until and active_from > active_until:
                raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания")

        for field, value in update_data.items():
            setattr(promo, field, value)

        promo.active = calculate_active(
            active_from=promo.active_from,
            active_until=promo.active_until
        )

        updated_promo = await self.repo.update_promo(promo)
        return TypeAdapter(PromoReadOnly).validate_python(updated_promo)

    async def get_promo_stat(self, promo_id: UUID, company_id: UUID) -> PromoStat:
        promo = await self.get_promo_by_id(promo_id, company_id)
        stat_data = await self.repo.get_promo_stat(promo.id)

        return PromoStat(
            activations_count=stat_data.total,
            countries=[
                CountryStat(country=country, activations_count=count)
                for country, count in sorted(
                    ((c, cnt) for c, cnt in stat_data.country_stats if c),
                    key=lambda x: x[0].lower()
                )
            ]
        )
