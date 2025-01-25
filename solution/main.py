import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from config import settings
from backend.redis import connect, close
from routers import auth, promo, auth_user, user_profile, user_promo

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



#docker exec -it fastapi_db bash
#psql -U postgres -d postgres
# DROP SCHEMA public CASCADE;
# CREATE SCHEMA public;
#\q
#exit
#docker exec -it fastapi_app alembic upgrade 2025_01_20_123456



#docker exec -it fastapi_app alembic revision --autogenerate -m "Initial migration"
#docker exec -it fastapi_app alembic upgrade header
#docker compose -f solution/docker-compose.yml build
#docker compose -f solution/docker-compose.yml up
#docker volume prune -f Удаляет все ненужные тома, включая том с базой данных
#
# {
#   "description": "Повышенный кэшбек 10% для новых клиентов банка!",
#   "image_url": "https://cdn2.thecatapi.com/images/3lo.jpg",
#   "target": {},
#   "max_count": 10,
#   "active_from": "2025-01-10",
#   "mode": "COMMON",
#   "promo_common": "sale-10"
# }
# {
#   "email": "Roma@example.com",
#   "password": "Roma2007!"
# }
#897cc5c7-1c96-48b2-acfa-6e3cfe38030c
# {
#   "description": "stringstri",
#   "image_url": "https://example.com/",
#   "target": {
#     "age_from": 22,
#     "age_until": 24,
#     "country": "Ru",
#     "categories": [
#       "string"
#     ]
#   },
#   "max_count": 10,
#   "active_from": "2025-03-23",
#   "active_until": "2025-04-25"
# }