from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from youtube_summarizer.api.routes import router
from youtube_summarizer.db.store import init_db

_BASE = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TradeLens", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(router)
