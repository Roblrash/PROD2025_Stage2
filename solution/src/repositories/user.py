from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from src.models.user import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar()

    async def create_user(self, user_data: dict) -> User:
        new_user = User(**user_data)
        self.session.add(new_user)
        try:
            await self.session.commit()
            await self.session.refresh(new_user)
            return new_user
        except IntegrityError as e:
            await self.session.rollback()
            raise ValueError("Email already registered") from e
