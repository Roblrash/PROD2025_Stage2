import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

from src.backend.redis import connect, close
from src.backend.config import settings
from src.routers import auth, promo, auth_user, user_profile, activate, user_promo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.url}: {exc}")
    return JSONResponse(status_code=400, content={"detail": "Invalid request data"})

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Value error on {request.url}: {exc}")
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.include_router(auth.router)
app.include_router(promo.router)
app.include_router(auth_user.router)
app.include_router(user_profile.router)
app.include_router(activate.router)
app.include_router(user_promo.router)

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    logger.info("Starting up application")
    app.state.redis = await connect()
    logger.info("Connected to Redis")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down application")
    await close(app.state.redis)
    logger.info("Redis connection closed")

if __name__ == "__main__":
    host = settings.SERVER_ADDRESS.split(":")[0]
    port = int(settings.SERVER_ADDRESS.split(":")[1])
    uvicorn.run(app, host=host, port=port)