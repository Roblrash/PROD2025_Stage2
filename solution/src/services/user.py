from fastapi import HTTPException
from passlib.context import CryptContext
from src.repositories.user_profile import UserRepository
from src.schemas.user_profile import User as UserSchema, UserPatch

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    async def get_profile(self, current_user) -> UserSchema:
        user = await self.repo.get_by_id(current_user.id)
        if not user:
            raise HTTPException(status_code=401, detail="User profile not found")

        user_data = {
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "other": user.other,
        }
        if user.avatar_url:
            user_data["avatar_url"] = user.avatar_url

        return UserSchema(**user_data)

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    async def update_profile(self, current_user, user_patch: UserPatch) -> UserSchema:
        user = await self.repo.get_by_id(current_user.id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        update_data = user_patch.dict(exclude_unset=True)
        if user_patch.avatar_url:
            update_data["avatar_url"] = str(user_patch.avatar_url)
        if "password" in update_data:
            update_data["password"] = self.hash_password(update_data["password"])

        for key, value in update_data.items():
            setattr(user, key, value)

        updated_user = await self.repo.update(user)

        user_data = {
            "name": updated_user.name,
            "surname": updated_user.surname,
            "email": updated_user.email,
            "other": updated_user.other,
        }
        if updated_user.avatar_url:
            user_data["avatar_url"] = updated_user.avatar_url

        return UserSchema(**user_data)
