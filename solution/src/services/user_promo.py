from uuid import UUID
from fastapi import HTTPException
from select import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.repositories.user_promo import PromoRepository
from src.repositories.comment import CommentRepository
from src.models.promocode import PromoCode
from src.models.comment import Commentary
from src.schemas.user_promo import PromoForUser, Comment, Author
from src.utils.promo_helpers import calculate_active
from src.utils.serializer import to_dict, uuid_to_str
from src.models.user import user_liked_promos

class PromoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.promo_repo = PromoRepository(db)
        self.comment_repo = CommentRepository(db)

    async def get_feed(self, current_user, limit: int, offset: int, category: str = None, active: bool = None):
        user_country = (current_user.other.get("country") or "").lower()
        user_age = current_user.other.get("age") or 0

        promos, total = await self.promo_repo.get_feed_promos(
            company_id=None,
            user_country=user_country,
            user_age=user_age,
            active=active,
            category=category,
            offset=offset,
            limit=limit,
        )

        response = []
        for promo in promos:
            promo_dict = to_dict(promo)
            is_activated = await self._is_activated_by_user(current_user.id, promo.promo_id)
            is_liked = await self._is_liked_by_user(current_user.id, promo.promo_id)

            promo_dict.update({
                "active": calculate_active(promo),
                "is_activated_by_user": is_activated,
                "is_liked_by_user": is_liked,
            })

            promo_data = PromoForUser(**promo_dict).dict(exclude_unset=True)
            promo_data = {k: uuid_to_str(v) for k, v in promo_data.items() if v is not None}
            response.append(promo_data)

        return response, total

    async def get_promo(self, promo_id: UUID, current_user) -> PromoForUser:
        promo = await self.promo_repo.get_by_id(promo_id)
        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден")
        promo_dict = to_dict(promo)
        is_activated = await self._is_activated_by_user(current_user.id, promo.promo_id)
        is_liked = await self._is_liked_by_user(current_user.id, promo.promo_id)
        promo_dict.update({
            "active": calculate_active(promo),
            "is_activated_by_user": is_activated,
            "is_liked_by_user": is_liked,
        })
        promo_data = PromoForUser(**promo_dict).dict(exclude_unset=True)
        return promo_data

    async def like_promo(self, promo_id: UUID, current_user) -> None:
        promo = await self.promo_repo.get_by_id(promo_id)
        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден")
        from src.models.user import user_liked_promos
        query = (
            select(user_liked_promos)
            .where(
                user_liked_promos.c.user_id == current_user.id,
                user_liked_promos.c.promo_id == promo_id
            )
        )
        result = await self.db.execute(query)
        if result.scalar():
            return

        insert_stmt = user_liked_promos.insert().values(user_id=current_user.id, promo_id=promo_id)
        await self.db.execute(insert_stmt)
        promo.like_count += 1
        await self.promo_repo.like_promo(promo)

    async def unlike_promo(self, promo_id: UUID, current_user) -> None:
        promo = await self.promo_repo.get_by_id(promo_id)
        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден")
        query = (
            select(user_liked_promos)
            .where(
                user_liked_promos.c.user_id == current_user.id,
                user_liked_promos.c.promo_id == promo_id
            )
        )
        result = await self.db.execute(query)
        if not result.scalar():
            return
        delete_stmt = user_liked_promos.delete().where(
            user_liked_promos.c.user_id == current_user.id,
            user_liked_promos.c.promo_id == promo_id
        )
        await self.db.execute(delete_stmt)
        promo.like_count = max(0, promo.like_count - 1)
        await self.promo_repo.like_promo(promo)

    async def create_comment(self, promo_id: UUID, current_user, text: str) -> dict:
        promo = await self.promo_repo.get_by_id(promo_id)
        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден")
        new_comment = Commentary(
            text=text,
            date=datetime.now(timezone.utc),
            author_id=current_user.id,
            promo_id=promo.promo_id
        )
        comment = await self.comment_repo.create_comment(new_comment)
        promo.comment_count += 1
        await self.promo_repo.update(promo)
        author = {
            "name": current_user.name,
            "surname": current_user.surname,
            "avatar_url": str(current_user.avatar_url) if current_user.avatar_url else None,
        }
        response = {
            "id": str(comment.id),
            "text": comment.text,
            "date": comment.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": author
        }
        return response

    async def get_comments(self, promo_id: UUID, offset: int, limit: int):
        comments, total = await self.comment_repo.get_comments(promo_id, offset, limit)
        formatted = []
        for comment in comments:
            author = {
                "name": comment.author.name,
                "surname": comment.author.surname,
                "avatar_url": str(comment.author.avatar_url) if comment.author.avatar_url else None,
            }
            if author.get("avatar_url") is None:
                author.pop("avatar_url", None)
            formatted.append({
                "id": str(comment.id),
                "text": comment.text,
                "date": comment.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "author": author
            })
        return formatted, total

    async def get_comment(self, promo_id: UUID, comment_id: UUID, current_user) -> dict:
        comment = await self.comment_repo.get_by_id(comment_id, promo_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Такого комментария не существует.")
        author = {
            "name": comment.author.name,
            "surname": comment.author.surname,
            "avatar_url": str(comment.author.avatar_url) if comment.author.avatar_url else None,
        }
        if author.get("avatar_url") is None:
            author.pop("avatar_url", None)
        return {
            "id": str(comment.id),
            "text": comment.text,
            "date": comment.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": author
        }

    async def edit_comment(self, promo_id: UUID, comment_id: UUID, current_user, new_text: str) -> dict:
        comment = await self.comment_repo.get_by_id(comment_id, promo_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Такого комментария не существует.")
        if comment.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Комментарий не принадлежит пользователю.")
        comment.text = new_text
        updated = await self.comment_repo.update(comment)
        author = {
            "name": updated.author.name,
            "surname": updated.author.surname,
            "avatar_url": str(updated.author.avatar_url) if updated.author.avatar_url else None,
        }
        if author.get("avatar_url") is None:
            author.pop("avatar_url", None)
        return {
            "id": str(updated.id),
            "text": updated.text,
            "date": updated.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": author
        }

    async def delete_comment(self, promo_id: UUID, comment_id: UUID, current_user) -> None:
        comment = await self.comment_repo.get_by_id(comment_id, promo_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Такого комментария не существует.")
        if comment.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Комментарий не принадлежит пользователю.")
        await self.comment_repo.delete(comment)
        promo = await self.promo_repo.get_by_id(promo_id)
        promo.comment_count = max(0, promo.comment_count - 1)
        await self.promo_repo.update(promo)

    async def _is_activated_by_user(self, user_id: UUID, promo_id: UUID) -> bool:
        from src.models.user import user_activated_promos, User
        query = select(User).where(User.id == user_id).join(user_activated_promos).filter(PromoCode.promo_id == promo_id)
        result = await self.db.execute(query)
        return result.scalar() is not None

    async def _is_liked_by_user(self, user_id: UUID, promo_id: UUID) -> bool:
        from src.models.user import user_liked_promos, User
        query = select(User).where(User.id == user_id).join(user_liked_promos).filter(PromoCode.promo_id == promo_id)
        result = await self.db.execute(query)
        return result.scalar() is not None
