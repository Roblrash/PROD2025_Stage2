from pydantic import BaseModel, EmailStr, conint, constr, field_validator, Field, conlist, model_validator
from typing import List, Optional
from uuid import UUID
from datetime import date
import pycountry
import re


class Target(BaseModel):
    age_from: Optional[conint(ge=0, le=100)] = None
    age_until: Optional[conint(ge=0, le=100)] = None
    country: Optional[constr(pattern=r'^[A-Za-z]{2}$')] = None
    categories: Optional[conlist(constr(min_length=2, max_length=20), min_length=0, max_length=20)] = None

    @field_validator('country')
    def validate_country(cls, value):
        if value is None:
            return value

        if not pycountry.countries.get(alpha_2=value.upper()):
            raise ValueError("Страна не существует в ISO 3166-1 alpha-2.")
        return value

    @model_validator(mode="after")
    def validate_age_range(cls, values):
        age_from = values.age_from
        age_until = values.age_until

        if age_from is not None and age_until is not None and age_from > age_until:
            raise ValueError("'age_from' cannot be greater than 'age_until'.")
        return values

class PromoPatch(BaseModel):
    description: Optional[constr(min_length=10, max_length=300)] = None
    image_url: Optional[constr(max_length=350)] = None
    target: Optional[Target] = None
    max_count: Optional[conint(ge=0)] = None
    active_from: Optional[str] = None
    active_until: Optional[str] = None

class PromoCreate(BaseModel):
    description: constr(min_length=10, max_length=300)
    image_url: Optional[constr(max_length=350)] = None
    target: Target
    max_count: conint(ge=0, le=100000000)
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    mode: constr(pattern=r'^(COMMON|UNIQUE)$')
    promo_common: Optional[constr(min_length=5, max_length=30)] = None
    promo_unique: Optional[conlist(constr(min_length=3, max_length=30), min_length=1, max_length=5000)] = None

    @model_validator(mode="after")
    def validate_mode_and_dependencies(cls, values):
        mode = values.mode
        promo_common = values.promo_common
        promo_unique = values.promo_unique
        max_count = values.max_count

        if mode == "COMMON":
            if not promo_common:
                raise ValueError("Field 'promo_common' is required when mode is 'COMMON'.")
            if promo_unique:
                raise ValueError("Field 'promo_unique' is not allowed when mode is 'COMMON'.")
        if mode == "UNIQUE":
            if not promo_unique:
                raise ValueError("Field 'promo_unique' is required when mode is 'UNIQUE'.")
            if promo_common:
                raise ValueError("Field 'promo_common' is not allowed when mode is 'UNIQUE'.")
            if max_count != 1:
                raise ValueError("Field 'max_count' must be 1 when mode is 'UNIQUE'.")

        return values

class PromoForUser(BaseModel):
    promo_id: UUID
    company_id: UUID
    company_name: str
    description: constr(min_length=10, max_length=300)
    image_url: str
    active: bool
    is_activated_by_user: bool
    like_count: conint(ge=0)
    is_liked_by_user: bool
    comment_count: conint(ge=0)

class PromoReadOnly(BaseModel):
    description: constr(min_length=10, max_length=300)
    image_url: Optional[constr(max_length=350)] = None
    target: Target
    max_count: conint(ge=0, le=100000000)
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    mode: constr(pattern=r'^(COMMON|UNIQUE)$')
    promo_common: Optional[constr(min_length=5, max_length=30)] = None
    promo_unique: Optional[List[constr(min_length=3, max_length=30)]] = None
    promo_id: UUID
    company_id: UUID
    company_name: str = Field(..., min_length=5, max_length=50)
    like_count: conint(ge=0)
    used_count: conint(ge=0)
    active: bool

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.strftime('%Y-%m-%d')
        }

class PromoStat(BaseModel):
    activations_count: conint(ge=0)
    countries: List[dict]


class UserTargetSettings(BaseModel):
    age: conint(ge=0)
    country: constr(pattern=r'^[A-Za-z]{2}$')

    @field_validator('country')
    def validate_country(cls, value):
        if value is None:
            return value

        value = value.upper()
        if not pycountry.countries.get(alpha_2=value):
            raise ValueError("Страна не существует в ISO 3166-1 alpha-2.")

        return value

class UserFirstName(BaseModel):
    first_name: constr(min_length=1, max_length=100)

class UserSurname(BaseModel):
    surname: constr(min_length=1, max_length=120)

class User(BaseModel):
    name: UserFirstName
    surname: UserSurname
    email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[str]
    other: UserTargetSettings

class UserRegister(BaseModel):
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class SignIn(BaseModel):
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class PromoId(BaseModel):
    promo_id: UUID

class CommentId(BaseModel):
    comment_id: UUID

class CompanyId(BaseModel):
    company_id: UUID

class CompanyResponse(BaseModel):
    token: str = Field(..., max_length=300)
    company_id: CompanyId

class SignInResponse(BaseModel):
    token: str = Field(..., max_length=300)

class CompanyName(BaseModel):
    company_name: str = Field(..., min_length=5, max_length=50)

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=5, max_length=50)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v
