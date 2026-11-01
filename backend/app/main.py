import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.bm25_store import get_bm25_store
from backend.app.config import settings
from backend.app.db import init_db
from backend.app.routers import admin, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("policypilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info(f"PolicyPilot starting: APP_ENV={settings.APP_ENV}, DEMO_MODE={settings.DEMO_MODE}")
    logger.info("Initializing SQLite database tables...")
    init_db()

    logger.info("Rebuilding BM25 index from SQLite chunks...")
    bm25 = get_bm25_store()
    bm25.rebuild()

    logger.info("PolicyPilot backend is ready to accept requests.")
    yield
    # Shutdown actions
    logger.info("PolicyPilot backend shutting down.")


app = FastAPI(
    title="PolicyPilot API",
    description="HR Policy RAG Chatbot with Source Citations",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
allowed_origins = list(
    dict.fromkeys(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            *(
                origin.strip().rstrip("/")
                for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
                if origin.strip()
            ),
        ]
    )
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "PolicyPilot",
        "version": "1.0.0"
    }
