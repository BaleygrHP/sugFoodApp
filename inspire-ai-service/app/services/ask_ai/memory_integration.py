from typing import Optional
from app.core.memory import get_memory_manager
from app.core.logger import get_logger

logger = get_logger(__name__)


async def retrieve_and_inject_memory(
    chatroom_id: Optional[str],
    ticket_id: Optional[str],
    current_query: str,
    additional_context: dict
) -> dict:
    """
    Retrieve and inject memory facts into additional context.

    Facts are filtered by relevance to current query and formatted for prompt injection.
    """
    if not chatroom_id:
        logger.warning("No chatroom_id provided, skipping memory retrieval")
        return additional_context

    try:
        memory_mgr = get_memory_manager()
        raw_facts = await memory_mgr.retrieve_context(
            chatroom_id=chatroom_id,
            ticket_id=ticket_id,
            query=current_query
        )

        if isinstance(raw_facts, dict) and "results" in raw_facts:
            results = [item.get("memory") for item in raw_facts["results"] if item.get("memory")]
        elif isinstance(raw_facts, list):
            results = raw_facts
        else:
            results = []

        additional_context["facts_context"] = results
        logger.info("[MEMORY] Facts context: %s", additional_context.get("facts_context"))

        return additional_context

    except Exception as e:
        logger.error(f"[MEMORY] Error retrieving memory: {str(e)}", exc_info=True)
        additional_context["facts_context"] = []
        return additional_context
