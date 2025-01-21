from pydantic import BaseModel, EmailStr, conint, constr, field_validator, Field, conlist, root_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import pycountry
import re


class Target(BaseModel):
    age_from: Optional[conint(ge=0, le=100)] = None
    age_until: Optional[conint(ge=0, le=100)] = None
    country: Optional[constr(pattern=r'^[A-Za-z]{2}$')] = None
    categories: Optional[conlist(constr(min_length=2, max_length=20), min_length=0, max_length=20)] = None


    @field_validator('country')
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
    image_url: Optional[constr(max_length=350)] = None
    target: Target
    max_count: conint(ge=0, le=100000000)
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    mode: constr(pattern=r'^(COMMON|UNIQUE)$')
    promo_common: Optional[constr(min_length=5, max_length=30)] = None
    promo_unique: Optional[conlist(constr(min_length=3, max_length=30), min_length=1, max_length=5000)] = None

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
    promo_unique: Optional[conlist(constr(min_length=3, max_length=30), min_length=1, max_length=5000)] = None
    promo_id: UUID
    company_id: UUID
    name: str = Field(..., min_length=5, max_length=50)
    like_count: conint(ge=0)
    used_count: conint(ge=0)
    active: bool

    @root_validator(pre=True)
    def check_active_status(cls, values):
        active_from = values.get('active_from')
        active_until = values.get('active_until')
        mode = values.get('mode')
        max_count = values.get('max_count')
        used_count = values.get('used_count')


        current_date = datetime.now()

        if active_from and datetime.fromisoformat(active_from) > current_date:
            values['active'] = False

        elif active_until and datetime.fromisoformat(active_until) < current_date:
            values['active'] = False

        elif mode == 'COMMON' and used_count is not None and max_count is not None and used_count >= max_count:
            values['active'] = False

        elif mode == 'UNIQUE' and not values.get('promo_unique'):
            values['active'] = False
        else:
            values['active'] = True

        return values

class PromoStat(BaseModel):
    activations_count: conint(ge=0)
    countries: List[dict]


class UserTargetSettings(BaseModel):
    age: conint(ge=0)
    country: constr(pattern=r'^[A-Za-z]{2}$')

    @field_validator('country')
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

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class SignIn(BaseModel):
    email: EmailStr
    password: str

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
