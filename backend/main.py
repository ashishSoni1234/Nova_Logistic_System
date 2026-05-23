from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from config import settings
from database import init_db

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Nova Platform API",
    description="AI-powered logistics workflow automation system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False,
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Files (uploaded documents) ────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ─── Routers ───────────────────────────────────────────────────────────────────
from routers.auth import router as auth_router
from routers.workflows import router as workflows_router
from routers.agents import router as agents_router
from routers.documents import router as documents_router
from routers.approvals import router as approvals_router
from routers.exceptions import router as exceptions_router
from routers.dashboard import router as dashboard_router

app.include_router(auth_router)
app.include_router(workflows_router)
app.include_router(agents_router)
app.include_router(documents_router)
app.include_router(approvals_router)
app.include_router(exceptions_router)
app.include_router(dashboard_router)


# ─── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Nova Platform API...")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    os.makedirs("uploads", exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    logger.info("Nova Platform API started successfully")


@app.get("/")
async def root():
    return {"message": "Nova Platform API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "nova-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=(settings.app_env == "development"),
        log_level="info",
    )
