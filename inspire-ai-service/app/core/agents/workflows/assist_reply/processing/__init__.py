"""Processing modules for AssistReply workflow.

This package contains modules for processing different aspects of the workflow:
- messages: Message segment processing and validation
- images: Image URL extraction and attachment
- context: Context building and chat history management
"""

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

__all__ = [
    # messages
    "normalize_segments",
    "validate_segments",
    "create_stop_event_result",
    # images
    "extract_image_urls",
    "has_images",
    # context
    "build_knowledge_context",
    "get_latest_user_message",
    "build_chat_history",
    "build_context_dicts",
    "build_topics",
]
