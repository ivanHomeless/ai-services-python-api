from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader, APIKey
from app.api.routers import speech_router
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set in environment")

# ---- Авторизация API Key ----
api_key_header = APIKeyHeader(name="x-token", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# ---- Создаём FastAPI с Swagger ----
app = FastAPI(
    title="AI Services API",
    description="API для работы с нейросетями",
    version="1.0.0"
)

# ---- Подключаем роутеры с авторизацией ----
app.include_router(
    speech_router.router,
    prefix="/api",
    dependencies=[Depends(get_api_key)],  # все эндпоинты требуют API Key
    tags=["Speech"]
)
