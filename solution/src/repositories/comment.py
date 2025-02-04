# src/repositories/comment.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID
from src.models.comment import Commentary

class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_comment(self, comment: Commentary) -> Commentary:
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def get_comments(self, promo_id: UUID, offset: int = 0, limit: int = 10) -> (list, int):
        query = select(Commentary).where(Commentary.promo_id == promo_id).order_by(Commentary.date.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        comments = result.scalars().all()

        count_query = select(func.count()).select_from(Commentary).where(Commentary.promo_id == promo_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return comments, total

    async def get_by_id(self, comment_id: UUID, promo_id: UUID) -> Commentary:
        query = select(Commentary).where(Commentary.id == comment_id, Commentary.promo_id == promo_id)
        result = await self.db.execute(query)
        return result.scalar()

    async def update(self, comment: Commentary) -> Commentary:
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete(self, comment: Commentary) -> None:
        await self.db.delete(comment)
        await self.db.commit()
