"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import mcp_runtime
from .config import settings
from .database import Base, SessionLocal, engine
from .repository import reconcile
from .routes.files import router
from .routes.settings import router as settings_router
from .routes.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reconcile(db)
    finally:
        db.close()
    yield
    await mcp_runtime.shutdown()


app = FastAPI(title="Agentic Filesystem API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(settings_router)
app.include_router(tasks_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
