import os

os.environ["OPENAI_USE_VOICE"] = "false"


from celery import Celery
from celery.schedules import crontab

from app.core.llm_config import configure_llm
from app.core.logger import get_logger
from app.settings import settings

#  Patch requests to make them non-blocking

logger = get_logger(__name__)


celery = Celery(
    'helpdesk-ai-agentic',
    broker=settings.infra.task_queue.message_broker,
    backend=settings.infra.task_queue.result_backend,
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=False,
)

celery.conf.beat_schedule = {
    "synchronize-datasources-daily": {
        "task": "reindex_all_datasources",
        "schedule": crontab(hour=settings.infra.task_queue.scheduled_hour, minute=settings.infra.task_queue.scheduled_minute),  # Run daily at 2:00 AM
        "options": {
            "expires": 3600  # Task expires after 1 hour if not executed
        },
    },
    "refresh-google-drive-channels": {
        "task": "refresh_google_drive_channels",
        "schedule": crontab(hour=0, minute=0, day_of_week='mon'),  # Run at midnight every Monday
        "options": {
            "expires": 3600  # Task expires after 1 hour if not executed
        },
    },
}


from .index_local_file import index_local_file  # noqa: E402
from .index_web import index_single_page, index_whole_website  # noqa: E402
from .index_products import index_products
# from .reindex_datasource import reindex_all_datasources  # noqa: E402
from .index_drive import index_google_drive, refresh_all_channels  # noqa: E402
from .reindex_datasource import reindex_all_datasources  # noqa: E402
from .extract_rules import extract_rules_from_histories  # noqa: E402
from .index_database_query import index_database_query # noqa: E402
from .draft_response import draft_response_async  # noqa: E402
from app.core.index_manager import get_index_manager  # noqa: E402

configure_llm()

__all__ = [
    "celery",
    "index_local_file",
    "get_index_manager",
    "index_single_page",
    "index_whole_website",
    "index_google_drive",
    "index_database_query",
    "refresh_all_channels",
    "logger",
    "reindex_all_datasources",
    "extract_rules_from_histories",
    "draft_response_async",
]
