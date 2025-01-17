from pydantic import BaseModel, EmailStr

class CompanyNameCreate(BaseModel):
    name: str

    class Config:
        min_length = 1
        max_length = 100

class Email(BaseModel):
    email: EmailStr

class Password(BaseModel):
    password: str
