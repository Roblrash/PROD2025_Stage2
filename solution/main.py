from fastapi import FastAPI
from solution.models import Base
from solution.backend.db import engine
from solution.routers import auth
from solution.config import settings

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from solution.routers import auth

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request data"}
    )

app.include_router(auth.router)

@app.get("/api/ping")
def send():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    import uvicorn
    server_host, server_port = settings.SERVER_ADDRESS.split(":") if settings.SERVER_ADDRESS else ("0.0.0.0", settings.SERVER_PORT)
    uvicorn.run(app, host=server_host, port=int(server_port))

