from fastapi import FastAPI
from pydantic import BaseModel

from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Voice API")

app.include_router(router)

#
# @app.get("/health")
# def health_check():
#     return {"status": "ok"}
#
#
#
# class TextRequest(BaseModel):
#     text: str
#
# @app.post("/echo")
# def echo(data: TextRequest):
#     return {"result": data.text}