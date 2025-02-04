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
from uuid import UUID
import re


class SignIn(BaseModel):
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)

    @field_validator("password")
    def validate_password(cls, v):
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,60}$"
        if not re.match(password_pattern, v):
            raise ValueError("Неправильный формат пароля")
        return v

class CompanyResponse(BaseModel):
    token: str = Field(..., max_length=300)
    company_id: UUID


class SignInResponse(BaseModel):
    token: str = Field(..., max_length=300)

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
