import os
import logging

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from app.api.routers import speech_router, image_router
from dotenv import load_dotenv

# --- 0. ПОДГОТОВКА ПАПОК ---
# Создаем папку logs автоматически, чтобы не было ошибки FileNotFoundError
os.makedirs("logs", exist_ok=True)

# --- 1. НАСТРОЙКА ЛОГИРОВАНИЯ ---
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

# Пишем теперь ВНУТРЬ папки logs
file_handler = logging.FileHandler("logs/providers.log", mode="a", encoding="utf-8")
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)


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

# Роутер изображений
app.include_router(
    image_router.router,
    prefix="/api/image",
    dependencies=[Depends(get_api_key)], # Та же защита
    tags=["Image Generation"]
)

logger.info("Application started! Logs directory is ready.")