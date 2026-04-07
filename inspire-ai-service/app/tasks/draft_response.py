import asyncio
import nest_asyncio
from app.services.ask_ai.ask_ai import AskAIService
from app.schemas.ask_ai.draft_response import DraftResponseDto
from app.core.tools.query_engine import get_query_engine
from app.services.ai_service import AIService
from . import celery, logger

# Allow nested event loops (needed for Celery + asyncio)
nest_asyncio.apply()


@celery.task(name="draft_response_async")
def draft_response_async(
    task_id: str,
    tenant_id: str,
    data: dict,
):
    """
    Background task to generate draft response.
    Sends status updates via AI-service callback.

    Args:
        task_id: Unique identifier for this task
        tenant_id: Tenant ID for the request
        data: Draft response request data

    Returns:
        dict with status and result/error
    """
    try:
        logger.info(f"[DRAFT-RESPONSE] Starting task {task_id} for tenant {tenant_id}")

        # Send processing status
        AIService.send_draft_response_callback(
            task_id=task_id,
            tenant_id=tenant_id,
            status="processing",
        )

        # Execute draft response generation
        # nest_asyncio allows us to use asyncio.run() in Celery workers
        async def _execute_draft_response():
            service = AskAIService()
            query_engine = get_query_engine()
            schema = DraftResponseDto(**data)
            return await service.draft_response(data=schema, query_engine=query_engine)

        result = asyncio.run(_execute_draft_response())

        # Send completion status with result
        AIService.send_draft_response_callback(
            task_id=task_id,
            tenant_id=tenant_id,
            status="completed",
            result=result.model_dump(),
        )

        logger.info(f"[DRAFT-RESPONSE] Task {task_id} completed successfully")
        return {"status": "completed", "result": result.model_dump()}

    except Exception as e:
        logger.error(f"[DRAFT-RESPONSE] Task {task_id} failed: {str(e)}", exc_info=True)

        # Send failure status
        AIService.send_draft_response_callback(
            task_id=task_id,
            tenant_id=tenant_id,
            status="failed",
            error=str(e),
        )

        raise
