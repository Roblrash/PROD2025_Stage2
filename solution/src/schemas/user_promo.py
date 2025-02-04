from datetime import datetime
from uuid import UUID
from pydantic import (
    BaseModel,
    EmailStr,
    conint,
    constr,
    field_validator,
    Field,
    model_validator,
    HttpUrl,
)
from typing import Optional


class PromoForUser(BaseModel):
    promo_id: UUID
    company_id: UUID
    company_name: str = Field(..., min_length=5, max_length=50)
    description: constr(min_length=10, max_length=300)
    image_url: Optional[str] = None
    active: bool
    is_activated_by_user: bool
    like_count: conint(ge=0)
    is_liked_by_user: bool
    comment_count: conint(ge=0)

    @model_validator(mode="after")
    def check_image_url_length(cls, values):
        image_url = values.image_url
        if image_url and len(str(image_url)) > 350:
            raise ValueError("URL must be at most 350 characters long.")
        return values

class CommentText(BaseModel):
    text: constr(min_length=10, max_length=1000)


class Author(BaseModel):
    name: constr(min_length=1, max_length=100)
    surname: constr(min_length=1, max_length=120)
    avatar_url: Optional[str] = None

    @model_validator(mode="after")
    def check_image_url_length(cls, values):
        avatar_url = values.avatar_url
        if avatar_url and len(str(avatar_url)) > 350:
            raise ValueError("URL must be at most 350 characters long.")
        return values

class Comment(BaseModel):
    id: UUID
    text: CommentText
    date: datetime
    author: Author