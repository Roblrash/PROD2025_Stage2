from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_, Integer, cast
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID
from src.models.promocode import PromoCode

class PromoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feed_promos(
        self,
        company_id: None,
        user_country: str,
        user_age: int,
        active: bool = None,
        category: str = None,
        offset: int = 0,
        limit: int = 10,
    ) -> (list, int):
        query = select(PromoCode)
        if active is not None:
            query = query.filter(PromoCode.active == active)

        country_filter = or_(
            func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country').is_(None),
            func.lower(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'country')) == user_country
        )
        query = query.filter(country_filter)

        age_filter = and_(
            or_(
                func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_from').is_(None),
                func.cast(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_from'), Integer) <= user_age
            ),
            or_(
                func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_until').is_(None),
                func.cast(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'age_until'), Integer) >= user_age
            )
        )
        query = query.filter(age_filter)

        if category:
            category = category.lower()
            category_filter = and_(
                func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories').isnot(None),
                func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories').notin_([""]),
                func.lower(func.jsonb_extract_path_text(cast(PromoCode.target, JSONB), 'categories')).contains(category)
            )
            query = query.filter(category_filter)

        count_query = query.with_only_columns(func.count(PromoCode.id)).order_by(None)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(PromoCode.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        promos = result.scalars().all()

        return promos, total

    async def get_by_id(self, promo_id: UUID) -> PromoCode:
        query = select(PromoCode).where(PromoCode.promo_id == promo_id)
        result = await self.db.execute(query)
        return result.scalar()

    async def update(self, promo: PromoCode) -> PromoCode:
        self.db.add(promo)
        await self.db.commit()
        await self.db.refresh(promo)
        return promo

    async def like_promo(self, promo: PromoCode) -> None:
        self.db.add(promo)
        await self.db.commit()
