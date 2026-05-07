from fastapi import APIRouter

from .agent import agent_router
from .ask import ask_router
from .ask_ai import ask_ai_router
from .food import food_router
from .knowledge import knowledge_router
from .knowledge_extractor import knowledge_extractor_router
from .health import health_router
from .media import media_router

api_router = APIRouter()
api_router.include_router(knowledge_router, tags=["Knowledge"])
api_router.include_router(knowledge_extractor_router, tags=["Knowledge Extractor"])
api_router.include_router(agent_router, tags=["Agent"])
api_router.include_router(ask_router, tags=["Ask"])
api_router.include_router(ask_ai_router, tags=["Ask AI"])
api_router.include_router(food_router, tags=["Food"])
api_router.include_router(media_router, tags=["Media"])
api_router.include_router(health_router, tags=["Health"])

__all__ = ["api_router"]
