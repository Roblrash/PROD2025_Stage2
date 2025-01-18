from pydantic import BaseModel, EmailStr, constr

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

