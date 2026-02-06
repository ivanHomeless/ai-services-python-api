from fastapi import APIRouter, HTTPException, Query, Header, Response
from fastapi.concurrency import run_in_threadpool
from app.services.image import generate_image_sync

router = APIRouter()

CREEPY_NEGATIVE_PROMPT = """
cartoon, anime, comic, sketch, drawing, painting, vector art, 3d render, plastic, low quality, worst quality, lowres, blurry, out of focus, depth of field, 
bokeh, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped, signature, watermark, username, text, error, bright, sunny, happy, vibrant colors, 
saturated, disfigured, ugly, mutation, deformed, glitched, artifacts, tiling, poorly drawn face, bad proportions, gross proportions, malformed limbs, missing arms, 
missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck
"""
@router.post("/generate", summary="Генерация изображения (Playground v2.5)")
async def generate_image_endpoint(
    prompt: str = Query(..., description="Описание изображения на английском"),
    negative_prompt: str = Query(CREEPY_NEGATIVE_PROMPT, description="Чего не должно быть"),
    width: int = Query(1024, ge=256, le=2048, description="Ширина"),
    height: int = Query(680, ge=256, le=2048, description="Высота (3:2)"),
    x_token: str = Header(..., description="API Key") # Оставляем для явности в Swagger, хотя main.py проверяет
):
    try:
        # Запускаем тяжелую функцию в threadpool, чтобы не блокировать API
        image_bytes = await run_in_threadpool(
            generate_image_sync,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height
        )

        # Возвращаем картинку напрямую.
        # n8n увидит это как бинарный файл.
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=generated_image.png"}
        )

    except TimeoutError:
        raise HTTPException(status_code=504, detail="Generation timed out (Space queue is too long)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")