"""Schemas for the chat app."""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.models.ask_ai.actions import ActionTypeEnum
from llama_index.core.llms import MessageRole
from app.services.ask_ai.constants.common import Channel, WorkflowMode
from app.schemas.ask_ai.message_segment import MessageSegment

DraftModeEnum = WorkflowMode

class ActionSchema(BaseModel):
    name: str
    description: str = ""
    condition: str = ""
    action_type: ActionTypeEnum
    type_config: dict

class TopicSchema(BaseModel):
    topic_name: str
    description: str
    instructions: list[str]
    actions: list[ActionSchema]
    default_topic_code: str | None = None


class ImageContentSchema(BaseModel):
    """Schema for image content in messages"""
    url: Optional[str] = Field(None, description="URL of the image")
    base64: Optional[str] = Field(None, description="Base64 encoded image data")
    mime_type: str = Field("image/jpeg", description="MIME type of the image")
    filename: Optional[str] = Field(None, description="Original filename")


class ChatMessageSchema(BaseModel):
    role: MessageRole = MessageRole.USER
    content: Optional[str] = None
    images: Optional[List[ImageContentSchema]] = Field(None, description="Optional list of images attached to this message")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        # Convert None to empty string
        return v if v is not None else ""

class CustomerContext(BaseModel):
    """Customer information for personalization"""
    customer_id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""



class TicketInfo(BaseModel):
    """Ticket context information"""
    ticket_id: str = ""
    status: str = ""
    source: str = ""
    priority: str = ""


class ConversationContext(BaseModel):
    """Conversation-level context and notes"""
    chatroom_id: str = ""
    internal_notes: list[str] = Field(default_factory=list)
    total_messages: int = 0
    last_agent_name: str | None = None


class DraftResponseDto(BaseModel):
    agent_name: str | None = None
    org_desc: str | None = None
    chat_history: list[ChatMessageSchema]
    rules: list[str] | None = None
    response_template: str | None = None
    topics: list[TopicSchema] | None = None
    channel: Channel | None = None
    tone: str | None = None
    language: str | None = None
    additional_context: dict[str, str] = {}
    doc_ids: Optional[list[str]] = Field(
        None, description="Optional document IDs to filter by"
    )
    user_id: str | None = None
    customer_context: dict | None = None
    email_metadata: dict | None = None
    ticket_info: dict | None = None
    conversation_context: dict | None = None

class DraftResponseResultDto(BaseModel):
    response: List[MessageSegment] = Field(
        default_factory=list,
        description="List of message segments to send sequentially"
    )
