import os
import uvicorn
from solution.backend.db_depends import get_db
from fastapi import FastAPI, Depends, HTTPException
from .schemas import CompanyNameCreate, Email, Password
from solution.routers.auth import register_company
from solution.backend.db import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
app = FastAPI()

@app.get("/api/ping")
def send():
    return {"status": "ok"}



@app.post("/business/auth/sign-up", response_model=dict)
async def sign_up_company(
    name: CompanyNameCreate,
    email: Email,
    password: Password,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await register_company(db=db, name=name, email=email, password=password)
    except HTTPException as e:
        raise e

if __name__ == "__main__":
    server_address = os.getenv("SERVER_ADDRESS", "0.0.0.0:8080")
    host, port = server_address.split(":")
    uvicorn.run(app, host=host, port=int(port))
