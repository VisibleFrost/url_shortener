from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from pydantic import BaseModel, HttpUrl
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import engine, Base, URLModel, get_db
from converter import converter
from redis import asyncio as aioredis
import os

async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

class URLShortenRequest(BaseModel):
    long_url: HttpUrl

@app.post("/shorten")
async def shorten_url(request: URLShortenRequest, db: AsyncSession = Depends(get_db)):
    url_str = str(request.long_url)

    result = await db.execute(select(URLModel).where(URLModel.long_url == url_str))
    existing_url = result.scalar_one_or_none()

    if existing_url:
        short_code = converter.encode(existing_url.id)

        await redis_client.set(short_code, url_str)

        return {
            "short_code": short_code,
            "short_url": f"http://localhost:8000/{short_code}",
            "info": "Эта ссылка уже была в базе! Вернули старый код."
        }

    db_url = URLModel(long_url=url_str)
    db.add(db_url)

    await db.commit()
    await db.refresh(db_url)
    short_code = converter.encode(db_url.id)

    await redis_client.set(short_code, url_str)
    
    return {
        "short_code": short_code,
        "short_url": f"http://localhost:8000/{short_code}"
    }

@app.get("/{short_code}")
async def redirect_to_long_url(short_code: str, db: AsyncSession = Depends(get_db)):
    try:
        url_id = converter.decode(short_code)
    except ValueError:
        raise HTTPException(status_code=400, detail="Невалидный код ссылки")
    
    cached_url = await redis_client.get(short_code)
    if cached_url:
        return RedirectResponse(url=cached_url, status_code=307)

    result = await db.execute(select(URLModel).where(URLModel.id == url_id))
    db_url = result.scalar_one_or_none()
    
    if not db_url:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    
    await redis_client.set(short_code, db_url.long_url)

    return RedirectResponse(url=db_url.long_url, status_code=307)