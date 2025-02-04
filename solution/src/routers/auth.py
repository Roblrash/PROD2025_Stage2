from fastapi import APIRouter, Depends
from src.schemas.company import CompanyResponse, CompanyCreate, SignIn, SignInResponse
from src.services.auth import AuthService
from src.dependencies.database import get_db, get_redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api")

@router.post("/business/auth/sign-up", response_model=CompanyResponse)
async def sign_up(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    auth_service = AuthService(db, redis)
    return await auth_service.sign_up(company_data)

@router.post("/business/auth/sign-in", response_model=SignInResponse)
async def sign_in(
    sign_in_data: SignIn,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    auth_service = AuthService(db, redis)
    return await auth_service.sign_in(
        email=sign_in_data.email,
        password=sign_in_data.password
    )
