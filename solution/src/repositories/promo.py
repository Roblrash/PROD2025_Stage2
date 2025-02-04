from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from src.models.promocode import PromoCode
from src.models.user import user_activated_promos

class PromoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_promo(self, promo: PromoCode) -> PromoCode:
        self.db.add(promo)
        await self.db.commit()
        await self.db.refresh(promo)
        return promo

    async def get_promos_by_company(
        self,
        company_id,
        filter_condition=None,
        offset: int = 0,
        limit: int = 10,
        sort_by: str = None
    ):
        query = select(PromoCode).filter(PromoCode.company_id == company_id)
        if filter_condition is not None:
            query = query.filter(filter_condition)
        if sort_by == "active_from":
            query = query.order_by(PromoCode.active_from.desc())
        elif sort_by == "active_until":
            query = query.order_by(PromoCode.active_until.desc())
        else:
            query = query.order_by(PromoCode.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_promos_by_company(self, company_id, filter_condition=None) -> int:
        query = select(func.count(PromoCode.id)).filter(PromoCode.company_id == company_id)
        if filter_condition is not None:
            query = query.filter(filter_condition)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_promo_by_id(self, promo_id: UUID) -> PromoCode:
        query = select(PromoCode).where(PromoCode.promo_id == promo_id)
        result = await self.db.execute(query)
        return result.scalar()

    async def update_promo(self, promo: PromoCode) -> PromoCode:
        self.db.add(promo)
        await self.db.commit()
        await self.db.refresh(promo)
        return promo

    async def get_promo_stat(self, promo_id: UUID) -> dict:
        total_query = select(func.count()).select_from(user_activated_promos).where(
            user_activated_promos.c.promo_id == promo_id
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        country_query = (
            select(
                func.jsonb_extract_path_text(PromoCode.target, 'country').label("country"),
                func.count().label("cnt")
            )
            .select_from(user_activated_promos)
            .group_by(func.jsonb_extract_path_text(PromoCode.target, 'country'))
            .where(user_activated_promos.c.promo_id == promo_id)
        )
        country_result = await self.db.execute(country_query)
        rows = country_result.all()
        return {"total": total_count, "country_stats": rows}
