from pydantic import (
    BaseModel,
    EmailStr,
    conint,
    constr,
    field_validator,
    Field,
    model_validator,
    HttpUrl
)
from typing import Optional
import pycountry
import re

class UserTargetSettings(BaseModel):
    age: conint(ge=0, le=100)
    country: constr(pattern=r'^[A-Za-z]{2}$')

    @field_validator('country')
    def validate_country(cls, value):
        if value is None:
            return value
        if not pycountry.countries.get(alpha_2=value.upper()):
            raise ValueError("Страна не существует в ISO 3166-1 alpha-2.")
        return value

class User(BaseModel):
    name: constr(min_length=1, max_length=100)
    surname: constr(min_length=1, max_length=120)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[str] = None
    other: UserTargetSettings

    @model_validator(mode="after")
    def check_image_url_length(cls, values):
        avatar_url = values.avatar_url
        if avatar_url and len(str(avatar_url)) > 350:
            raise ValueError("URL must be at most 350 characters long.")
        return values

class UserRegister(BaseModel):
    name: constr(min_length=1, max_length=100)
    surname: constr(min_length=1, max_length=120)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[HttpUrl] = None
    other: UserTargetSettings
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

    @model_validator(mode="after")
    def check_image_url_length(cls, values):
        avatar_url = values.avatar_url
        if avatar_url and len(str(avatar_url)) > 350:
            raise ValueError("URL must be at most 350 characters long.")
        return values

class SignIn(BaseModel):
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class SignInResponse(BaseModel):
    token: str = Field(..., max_length=300)