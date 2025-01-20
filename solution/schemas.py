from pydantic import BaseModel, EmailStr, conint, constr, validator, Field
from typing import List, Optional
from uuid import UUID
import pycountry
import re


class Target(BaseModel):
    age_from: Optional[conint(ge=0)] = None
    age_until: Optional[conint(ge=0)] = None
    country: Optional[constr(pattern=r'^[A-Za-z]{2}$')] = None
    categories: Optional[List[str]] = None


    @validator('country')
    def validate_country(cls, value):
        value = value.upper()
        if not pycountry.countries.get(alpha_2=value):
            raise ValueError("Страна не существует в ISO 3166-1 alpha-2.")

        return value

class PromoPatch(BaseModel):
    description: constr(min_length=10, max_length=300)
    image_url: str
    target: Target
    max_count: Optional[conint(ge=0)] = None
    active_from: Optional[str]
    active_until: Optional[str]

class PromoCreate(BaseModel):
    description: constr(min_length=10, max_length=300)
    image_url: str
    target: Target
    max_count: conint(ge=1)
    active_from: str
    active_until: Optional[str] = None
    mode: constr(pattern=r'^(COMMON|UNIQUE)$')
    promo_common: Optional[str] = None
    promo_unique: Optional[List[str]] = None

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
    image_url: str
    target: Target
    max_count: conint(ge=1)
    active_from: str
    active_until: str
    mode: constr(pattern=r'^(COMMON|UNIQUE)$')
    promo_common: Optional[str] = None
    promo_unique: Optional[List[str]] = None
    promo_id: UUID
    company_id: UUID
    company_name: str
    like_count: conint(ge=0)
    used_count: conint(ge=0)
    active: bool

class PromoStat(BaseModel):
    activations_count: conint(ge=0)
    countries: List[dict]


class UserTargetSettings(BaseModel):
    age: conint(ge=0)
    country: constr(pattern=r'^[A-Za-z]{2}$')

    @validator('country')
    def validate_country(cls, value):
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
    email: EmailStr
    avatar_url: Optional[str]
    other: UserTargetSettings

class UserRegister(BaseModel):
    email: str
    password: str

    @validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class SignIn(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
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

    @validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v
