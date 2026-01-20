from fastapi import FastAPI, Header, HTTPException
from app.api.routes import router
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set in environment")
app = FastAPI(title="Di API")

# Примитивная проверка ключа через middleware
@app.middleware("http")
async def check_api_key(request, call_next):
    key = request.headers.get("x-api-key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    response = await call_next(request)
    return response

app.include_router(router)