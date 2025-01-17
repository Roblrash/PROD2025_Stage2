from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("POSTGRES_CONN_ASYNC")

# Асинхронное подключение к базе данных
engine = create_async_engine(DATABASE_URL, echo=True)

# Используем async_sessionmaker для создания сессий
async_session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()
