import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from config import settings
from backend.redis import connect, close
from routers import auth, promo, auth_user, user_profile, user_promo, activate

app = FastAPI()

#def load_openapi_schema():
#     openapi_path = Path("api.yml")
#     if openapi_path.exists():
#         with open(openapi_path, mode="r", encoding="utf8") as f:
#             openapi_schema = yaml.safe_load(f)
#             return openapi_schema
#     return None
#
#app.openapi_schema = load_openapi_schema()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request data"}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

app.include_router(auth.router)
app.include_router(promo.router)
app.include_router(auth_user.router)
app.include_router(user_profile.router)
app.include_router(activate.router)
app.include_router(user_promo.router)

@app.get("/api/ping")
def send():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    app.state.redis = await connect()

@app.on_event("shutdown")
async def shutdown():
    await close(app.state.redis)

if __name__ == "__main__":
    server_host, server_port = settings.SERVER_ADDRESS.split(":")
    uvicorn.run(app, host=server_host, port=int(server_port))