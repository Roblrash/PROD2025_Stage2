from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.backend.db import get_db
from src.models.user import User
from src.schemas import User as UserSchema, UserPatch
from src.routers.auth_user import hash_password
from src.dependencies import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/user")

@router.get("/profile", response_model=UserSchema)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar()

    if not user:
        raise HTTPException(status_code=401, detail="User profile not found")

    user_data = {
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "other": user.other
    }

    if user.avatar_url:
        user_data["avatar_url"] = user.avatar_url

    user_data = UserSchema(**user_data).dict(exclude_unset=True)
    response_data = {key: value for key, value in user_data.items() if value is not None}

    return JSONResponse(content=response_data)


@router.patch("/profile", response_model=UserSchema)
async def update_user_profile(
        user_patch: UserPatch,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    update_data = user_patch.dict(exclude_unset=True)

    if user_patch.avatar_url:
        update_data["avatar_url"] = str(user_patch.avatar_url)

    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    user_data = {
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "other": user.other
    }

    if user.avatar_url:
        user_data["avatar_url"] = user.avatar_url

    user_data = UserSchema(**user_data).dict(exclude_unset=True)
    response_data = {key: value for key, value in user_data.items() if value is not None}

    return JSONResponse(content=response_data)
