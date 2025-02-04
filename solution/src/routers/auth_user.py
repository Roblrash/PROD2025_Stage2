from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.backend.db import get_db
from src.schemas.user import UserRegister, SignIn, SignInResponse
from src.services.auth_user import AuthService

router = APIRouter(prefix="/api/user/auth")

def get_redis(request: Request) -> Redis:
    return request.app.state.redis

@router.post("/sign-up", response_model=SignInResponse)
async def register_user(
    user: UserRegister,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    auth_service = AuthService(db, redis)
    return await auth_service.register_user(user)

@router.post("/sign-in", response_model=SignInResponse)
async def sign_in(
    user: SignIn,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    auth_service = AuthService(db, redis)
    return await auth_service.sign_in(user.email, user.password)
