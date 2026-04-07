"""Context building and chat history management.

This module handles building conversation context, extracting messages,
and managing chat history for the AssistReply workflow.
"""

from typing import Any, List
from base64 import b64decode
import requests

from llama_index.core.llms import ChatMessage, ImageBlock

from app.core.agents.workflows.assist_reply.processing.images import has_images
from app.models.ask_ai.actions import ACTION_CLASSES, Action
from app.models.ask_ai.utils import Topic


def get_latest_user_message(chat_history: List[Any]) -> str:
    """Extract the latest user message from chat history.

    Args:
        chat_history: List of chat messages

    Returns:
        Latest user message text, or "[Image]" if only image, or "" if none found
    """
    for message in reversed(chat_history or []):
        role_value = getattr(message, "role", "") or ""
        role_string = str(role_value).lower()
        if "user" not in role_string:
            continue

        raw_content = getattr(message, "content", None)
        if raw_content is None:
            content_text = ""
        elif isinstance(raw_content, str):
            content_text = raw_content.strip()
        else:
            try:
                content_text = str(raw_content).strip()
            except (TypeError, ValueError, AttributeError):
                content_text = ""

        if content_text:
            return content_text

        if has_images(message):
            return "[Image]"

    return ""


def build_knowledge_context(
    chat_history: List[Any], conversation_context: str | None, max_messages: int = 5
) -> str:
    """Build context string for knowledge base queries.

    Args:
        chat_history: List of chat messages
        conversation_context: Optional pre-built context string
        max_messages: Maximum messages to include (currently unused, reserved for future)

    Returns:
        Context string for knowledge base queries
    """
    if isinstance(conversation_context, str) and conversation_context.strip():
        return conversation_context.strip()
    latest = get_latest_user_message(chat_history)
    return latest.strip() if latest else ""


def build_chat_history(chat_messages: list[Any]) -> list[ChatMessage]:
    """Build LlamaIndex ChatMessage list from raw messages.

    Handles image attachments from base64 or URLs.

    Args:
        chat_messages: Raw chat message objects

    Returns:
        List of LlamaIndex ChatMessage objects with image blocks
    """
    chat_history: list[ChatMessage] = []
    for msg in (chat_messages or []):
        chat_msg = ChatMessage(
            role=getattr(msg, "role", None), content=getattr(msg, "content", "") or ""
        )
        imgs = getattr(msg, "images", None) or []
        for img in imgs:
            base64_str = getattr(img, "base64", None)
            url = getattr(img, "url", None)
            mime_type = getattr(img, "mime_type", "image/jpeg")
            if base64_str:
                try:
                    decoded = b64decode(base64_str)
                    chat_msg.blocks.append(ImageBlock(image=decoded, mime_type=mime_type))
                except Exception:
                    pass
            elif url:
                try:
                    clean_url = url.rstrip(":").strip()
                    if not clean_url.startswith(("http://", "https://")):
                        clean_url = "http://" + clean_url
                    response = requests.get(clean_url, timeout=(5, 30))
                    if response.status_code == 200:
                        mt = mime_type or response.headers.get("content-type", "image/jpeg")
                        chat_msg.blocks.append(ImageBlock(image=response.content, mime_type=mt))
                except Exception:
                    pass
        chat_history.append(chat_msg)
    return chat_history


def build_context_dicts(
    data: Any,
) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    """Extract context dictionaries from workflow data.

    Args:
        data: Workflow data object

    Returns:
        Tuple of (customer_context, email_metadata, ticket_info, conversation_context)
    """
    customer_context = getattr(data, "customer_context", None) or None
    email_metadata = getattr(data, "email_metadata", None) or None
    ticket_info = getattr(data, "ticket_info", None) or None
    conversation_context = getattr(data, "conversation_context", None) or None
    return customer_context, email_metadata, ticket_info, conversation_context


def build_topics(topic_schemas: list[Any] | None, user_id: str | None) -> list[Topic]:
    """Build Topic objects with actions from topic schemas.

    Args:
        topic_schemas: List of topic schema objects
        user_id: User ID for action initialization

    Returns:
        List of Topic objects with initialized actions
    """
    topics: list[Topic] = []
    if not topic_schemas:
        return topics
    for topic in topic_schemas:
        actions = [
            ACTION_CLASSES.get(getattr(action, "action_type", None), Action)(
                **{**action.model_dump(), **getattr(action, "type_config", {}), "user_id": user_id}
            )
            for action in getattr(topic, "actions", [])
        ]
        topics.append(
            Topic(
                topic_name=getattr(topic, "topic_name", ""),
                description=getattr(topic, "description", ""),
                instructions=getattr(topic, "instructions", []) or [],
                actions=actions,
                default_topic_code=getattr(topic, "default_topic_code", None),
            )
        )
    return topics
