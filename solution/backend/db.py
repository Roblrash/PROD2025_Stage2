from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=True
)

async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session


class Base(DeclarativeBase):
    pass