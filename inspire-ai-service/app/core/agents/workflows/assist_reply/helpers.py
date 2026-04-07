"""Legacy helpers module - DEPRECATED.

This module is deprecated and will be removed in a future version.
All functions have been moved to processing/* modules:
- messages.py: normalize_segments, validate_segments, create_stop_event_result
- images.py: extract_image_urls, has_images
- context.py: build_knowledge_context, get_latest_user_message, build_chat_history, build_context_dicts, build_topics

Please update imports to use the new modules:
    from app.core.agents.workflows.assist_reply.processing import (
        normalize_segments, validate_segments, create_stop_event_result,
        extract_image_urls, has_images,
        build_knowledge_context, get_latest_user_message, build_chat_history, build_topics
    )
"""

import warnings
from typing import Any, List, Callable
import asyncio

from app.core.agents.workflows.assist_reply.config import get_config

# Import from processing modules for backward compatibility
from app.core.agents.workflows.assist_reply.processing.messages import (
    normalize_segments,
    validate_segments,
    create_stop_event_result,
)
from app.core.agents.workflows.assist_reply.processing.images import (
    extract_image_urls,
    has_images,
)
from app.core.agents.workflows.assist_reply.processing.context import (
    build_knowledge_context,
    get_latest_user_message,
    build_chat_history,
    build_context_dicts,
    build_topics,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "The helpers module is deprecated. Import from "
    "'app.core.agents.workflows.assist_reply.processing' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Get configuration instance
_config = get_config()

# Deprecated: Use config.get_config() instead
PARALLEL_AGENT_TIMEOUT = _config.parallel_agent_timeout
KNOWLEDGE_TIMEOUT = _config.knowledge_timeout
KNOWLEDGE_TOP_K = _config.knowledge_top_k
LLM_TIMEOUT = _config.llm_timeout


# Agent execution functions (still needed in helpers for now)
async def run_init_agent(init_agent: Any, chat_history: List[Any]) -> str:
    """Run init agent and return content with explicit error handling.

    Returns:
        Agent output string, or empty string on error (with logging)
    """
    from llama_index.core.agent.workflow import AgentWorkflow
    from app.core.logger import get_logger

    logger = get_logger(__name__)
    agent_name = getattr(init_agent, "name", "Init Agent")

    try:
        init_workflow = AgentWorkflow(
            agents=[init_agent], root_agent=init_agent.name, initial_state={}
        )
        handler = init_workflow.run(chat_history=chat_history.copy())
        parts: List[str] = []

        try:
            async for event in handler.stream_events():
                try:
                    if hasattr(event, "response") and hasattr(event.response, "content"):
                        content = getattr(event.response, "content", None)
                        if isinstance(content, str) and content:
                            parts.append(content)
                except Exception as e:
                    # Log event processing errors but continue collecting other events
                    logger.warning(
                        f"[ErrorHandling] {agent_name} event processing error: "
                        f"{type(e).__name__}: {str(e)[:100]}"
                    )
                    continue

        except asyncio.CancelledError:
            logger.warning(f"[ErrorHandling] {agent_name} execution cancelled")
            return ""
        except Exception as e:
            logger.error(
                f"[ErrorHandling] {agent_name} stream iteration failed: "
                f"{type(e).__name__}: {str(e)[:200]}",
                exc_info=True,
            )
            return ""

        result = " ".join(parts) if parts else ""
        if not result:
            logger.info(f"[ErrorHandling] {agent_name} returned empty content")
        return result

    except Exception as e:
        logger.error(
            f"[ErrorHandling] {agent_name} initialization/execution failed: "
            f"{type(e).__name__}: {str(e)[:200]}",
            exc_info=True,
        )
        return ""


async def run_topic_agents_parallel(
    executor: Callable[..., Any], agents: List[Any], chat_history: List[Any], timeout: float | None = None
) -> List[str]:
    """Run topic agents in parallel with explicit error handling.

    Args:
        executor: Parallel executor function
        agents: List of agents to run
        chat_history: Conversation history
        timeout: Timeout per agent (default: from config)

    Returns:
        List of agent output strings (empty strings for failed agents are filtered out)
    """
    from app.core.logger import get_logger

    logger = get_logger(__name__)

    if not agents:
        return []

    # Use config timeout if not specified
    if timeout is None:
        timeout = get_config().parallel_agent_timeout

    try:
        result = await executor(
            agents=agents, chat_history=chat_history.copy(), timeout_per_agent=timeout
        )

        if isinstance(result, Exception):
            logger.error(
                f"[ErrorHandling] Parallel executor raised exception: "
                f"{type(result).__name__}: {str(result)[:200]}",
                exc_info=result,
            )
            return []

        # Filter out empty strings (failed/empty agents)
        outputs = [out for out in result if isinstance(out, str) and out.strip()]

        if len(outputs) < len(agents):
            failed_count = len(agents) - len(outputs)
            logger.warning(
                f"[ErrorHandling] {failed_count}/{len(agents)} agents returned empty content"
            )

        return outputs

    except Exception as e:
        logger.error(
            f"[ErrorHandling] Parallel agent execution failed: "
            f"{type(e).__name__}: {str(e)[:200]}",
            exc_info=True,
        )
        return []


async def run_knowledge_query(
    query_engine: Any, context_text: str, top_k: int | None = None, timeout: float | None = None
) -> Any:
    """Query knowledge base with explicit error handling.

    Args:
        query_engine: Query engine instance
        context_text: Query text
        top_k: Number of results (default: from config)
        timeout: Timeout in seconds (default: from config)

    Returns:
        Query results dict with sources, or None on error (with logging)
    """
    from app.core.logger import get_logger

    logger = get_logger(__name__)

    if not query_engine or not context_text:
        return None

    # Use config values if not specified
    if top_k is None:
        top_k = get_config().knowledge_top_k
    if timeout is None:
        timeout = get_config().knowledge_timeout

    try:
        # Sources-only retrieval to avoid extra LLM generation in the retriever
        result = await asyncio.wait_for(
            query_engine.aquery(context_text, top_k=top_k, extract_full=False),
            timeout=timeout,
        )
        return result

    except asyncio.TimeoutError:
        logger.warning(
            f"[ErrorHandling] Knowledge query timed out after {timeout}s | "
            f"query_length={len(context_text)} top_k={top_k}"
        )
        return None
    except Exception as e:
        logger.error(
            f"[ErrorHandling] Knowledge query failed: {type(e).__name__}: {str(e)[:200]} | "
            f"query_length={len(context_text)} top_k={top_k}",
            exc_info=True,
        )
        return None


# Export all for backward compatibility
__all__ = [
    # Config constants (deprecated)
    "PARALLEL_AGENT_TIMEOUT",
    "KNOWLEDGE_TIMEOUT",
    "KNOWLEDGE_TOP_K",
    "LLM_TIMEOUT",
    # Agent execution
    "run_init_agent",
    "run_topic_agents_parallel",
    "run_knowledge_query",
    # Re-exported from processing.messages
    "normalize_segments",
    "validate_segments",
    "create_stop_event_result",
    # Re-exported from processing.images
    "extract_image_urls",
    "has_images",
    # Re-exported from processing.context
    "build_knowledge_context",
    "get_latest_user_message",
    "build_chat_history",
    "build_context_dicts",
    "build_topics",
]
