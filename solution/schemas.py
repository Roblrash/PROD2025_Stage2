from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List, Literal
from datetime import date

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class CompanyResponse(BaseModel):
    token: str
    company_id: int

class SignInResponse(BaseModel):
    token: str
    company_id: int

class SignInRequest(BaseModel):
    username: str
    password: str

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
    type: Literal["COMMON", "UNIQUE"]
    code: Optional[str] = None
    codes: Optional[List[str]] = None
    limit: int = Field(0, ge=0)
    target: PromoTarget = Field(default_factory=PromoTarget)
    active_from: Optional[date] = None
    active_until: Optional[date] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def check_logic(self) -> "PromoCreate":
        if self.type == "COMMON":
            if not self.code:
                raise ValueError("For type=COMMON, 'code' is required.")
            if self.codes:
                raise ValueError("For type=COMMON, 'codes' must be empty or omitted.")
        elif self.type == "UNIQUE":
            if not self.codes or len(self.codes) == 0:
                raise ValueError("For type=UNIQUE, 'codes' is required and cannot be empty.")
            if self.code:
                raise ValueError("For type=UNIQUE, 'code' must be empty or omitted.")
        return self
