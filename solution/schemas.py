from pydantic import BaseModel, EmailStr, Field, model_validator, constr, HttpUrl
from typing import Optional, List, Literal
from datetime import date

class CompanyCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    email: EmailStr
    password: constr(min_length=8, max_length=128)

class CompanyResponse(BaseModel):
    token: str
    company_id: int


class SignInRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)


class SignInResponse(BaseModel):
    token: str
    company_id: int

class PromoTarget(BaseModel):
    age_from: Optional[int] = None
    age_until: Optional[int] = None
    country: Optional[str] = None

    @model_validator(mode="after")
    def check_ages(self) -> "PromoTarget":
        if self.age_from is not None and self.age_until is not None:
            if self.age_from > self.age_until:
                raise ValueError("age_from must be <= age_until")
        return self

class PromoCreate(BaseModel):
    mode: Literal["COMMON", "UNIQUE"]
    promo_common: Optional[str] = None
    promo_unique: Optional[List[str]] = None
    max_count: int = Field(..., ge=0)
    target: Optional[PromoTarget] = None
    active_from: Optional[date] = None
    active_until: Optional[date] = None
    description: Optional[str] = None
    image_url: Optional[HttpUrl] = None

    @model_validator(mode="after")
    def check_logic(self) -> "PromoCreate":
        if self.mode == "COMMON":
            if not self.code:
                raise ValueError("For type=COMMON, 'code' is required.")
            if self.codes:
                raise ValueError("For type=COMMON, 'codes' must be empty or omitted.")
        elif self.mode == "UNIQUE":
            if not self.codes or len(self.codes) == 0:
                raise ValueError("For type=UNIQUE, 'codes' is required and cannot be empty.")
            if self.mode:
                raise ValueError("For type=UNIQUE, 'code' must be empty or omitted.")
        return self
