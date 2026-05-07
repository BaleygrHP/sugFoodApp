import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import api_router
from app.core.index_manager import get_index_manager
from app.core.logger import get_logger
from app.middlewares.logging import log_requests
from app.settings import settings
from app.core.llm_config import configure_llm
from exceptions import setup_exception_handlers


load_dotenv(override=True)

logger = get_logger(__name__)


def get_ai_service_mode():
    return os.getenv("AI_SERVICE_MODE", "food_chat").strip().lower()


def setup_directories():
    os.makedirs(settings.infra.file_storage.data_dir, exist_ok=True)
    os.makedirs(settings.infra.file_storage.static_dir, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_directories()
    configure_llm()
    ai_service_mode = get_ai_service_mode()
    app.state.ai_service_mode = ai_service_mode

    if ai_service_mode == "full":
        app.state.index_manager = get_index_manager()
        logger.info(f"Index manager initialized with vector store type: {settings.infra.vector_store.type}")
    else:
        app.state.index_manager = None
        logger.info("AI service started in food_chat mode; skipping knowledge index initialization.")

    yield
    logger.info("Shutting down LlamaIndex application...")


# App initialization with lifespan
app = FastAPI(title=" AI Module", version="1.0.0", lifespan=lifespan)
setup_exception_handlers(app)

# Add logging middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.0.109.61:3000", 
        "http://localhost:3000",   
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure CORS based on environment
environment = os.getenv("ENVIRONMENT", "dev")
if environment == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+|http://0\.0\.0\.0:\d+",
        allow_origins=[
        "http://10.0.109.61:3000", 
        "http://localhost:3000",   
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "10.0.109.61")
    app_port = int(os.getenv("APP_PORT", "8000"))
    reload = environment == "dev"

    import uvicorn

    uvicorn.run(app="main:app", host=app_host, port=app_port, reload=reload)
