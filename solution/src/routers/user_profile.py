from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from src.backend.db import get_db
from src.services.user import UserService
from src.schemas.user_profile import User as UserSchema, UserPatch
from src.utils.get_company_or_user import get_current_user

router = APIRouter(prefix="/api/user")

@router.get("/profile", response_model=UserSchema)
async def get_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    profile = await service.get_profile(current_user)
    return JSONResponse(content=profile.dict(exclude_unset=True))

@router.patch("/profile", response_model=UserSchema)
async def update_user_profile(
    user_patch: UserPatch,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    profile = await service.update_profile(current_user, user_patch)
    return JSONResponse(content=profile.dict(exclude_unset=True))
