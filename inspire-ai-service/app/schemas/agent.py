from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ImageContent(BaseModel):
    """Schema for image content in messages"""
    url: Optional[str] = Field(None, description="URL of the image")
    base64: Optional[str] = Field(None, description="Base64 encoded image data")
    mime_type: str = Field("image/jpeg", description="MIME type of the image")
    filename: Optional[str] = Field(None, description="Original filename")


class ChatMessageWithImages(BaseModel):
    """Schema for chat message with optional image attachments"""
    role: str = Field(..., description="Role of the message sender (user/assistant/system)")
    content: str = Field(..., description="Text content of the message")
    images: Optional[List[ImageContent]] = Field(None, description="Optional list of images")


class QuestionDto(BaseModel):
    question: str = Field(..., description="The question to ask the AI assistant")
    doc_ids: Optional[List[str]] = Field(
        default=None, description="List of document IDs to query from vector store"
    )
    system_prompt: Optional[str] = Field(
        None, description="Optional system instructions for the agent"
    )
    chat_history: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional chat history for context. Each message can include 'images' field with list of image objects.",
        examples=[
            [
                {"role": "user", "content": "What is the capital of Vietnam?"},
                {"role": "assistant", "content": "The capital of Vietnam is Ha Noi."},
            ]
        ],
    )
    temperature: Optional[float] = Field(
        default=0.7, description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        default=1000, description="Maximum number of tokens for the response"
    )


class DirectQueryDto(BaseModel):
    """Request schema for direct RAG queries"""

    question: str = Field(..., description="The question to ask")
    doc_ids: Optional[List[str]] = Field(
        None, description="Optional document IDs to filter by"
    )
    top_k: int = Field(5, description="Number of documents to retrieve")


class CompletionDto(BaseModel):
    """Request schema for pure LLM completions"""

    prompt: str = Field(..., description="The prompt to complete")
    system_prompt: Optional[str] = Field(
        None, description="Optional system instructions"
    )
    temperature: Optional[float] = Field(
        None, description="Optional temperature for LLM"
    )
    max_tokens: Optional[int] = Field(
        None, description="Optional max tokens for LLM response"
    )


class ChatCompletionDto(BaseModel):
    """Request schema for chat completions"""
    prompt: Optional[str] = Field(
        None, description="Optional prompt for the chat completion"
    )
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="List of chat messages. Each message can include 'images' field with list of image objects.",
        examples=[
            [
                {"role": "user", "content": "What is the capital of Vietnam?"},
                {"role": "assistant", "content": "The capital of Vietnam is Ha Noi."},
            ]
        ],
    )
    system_prompt: Optional[str] = Field(
        None, description="Optional system instructions"
    )
    temperature: Optional[float] = Field(
        None, description="Optional temperature for LLM"
    )
    max_tokens: Optional[int] = Field(
        None, description="Optional max tokens for LLM response"
    )


class EnhancedChatCompletionDto(BaseModel):
    prompt: Optional[str] = Field(None, description="Current user message")
    messages: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Previous conversation messages. Each message can include 'images' field with list of image objects.",
        examples=[
            [
                {"role": "user", "content": "What is the capital of Vietnam?"},
                {"role": "assistant", "content": "The capital of Vietnam is Ha Noi."},
            ]
        ],
    )
    system_prompt: Optional[str] = Field(None, description="System instructions")
    use_knowledge: Optional[bool] = Field(True, description="Whether to use RAG")
    top_k: Optional[int] = Field(3, description="Number of documents to retrieve")
    doc_ids: Optional[List[str]] = Field(None, description="Document IDs to filter")
    temperature: Optional[float] = Field(None, description="Temperature for generation")
    max_tokens: Optional[int] = Field(None, description="Max response tokens")
