from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.company import Company
from sqlalchemy.exc import IntegrityError

class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_company(self, company_data: dict) -> Company:
        new_company = Company(**company_data)
        self.session.add(new_company)
        try:
            await self.session.commit()
            await self.session.refresh(new_company)
            return new_company
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(status_code=409, detail="Email already exists")

    async def get_by_email(self, email: str) -> Company:
        result = await self.session.execute(select(Company).where(Company.email == email))
        return result.scalar()