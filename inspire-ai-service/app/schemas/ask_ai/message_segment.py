from pydantic import BaseModel, Field
from typing import List


class MessageAttachment(BaseModel):
    type: str = Field(..., description="Attachment type: 'image' | 'file' | 'video'")
    url: str = Field(..., description="URL of the attachment")
    name: str = Field(default="", description="Filename")


class MessageSegment(BaseModel):
    content: str = Field(default="", description="Message text content")
    order: int = Field(..., description="Sequence order (1-indexed)", ge=1)
    delay_ms: int = Field(default=0, description="Delay in milliseconds", ge=0)
    type: str = Field(default="text", description="Message type: 'text' | 'image' | 'file' | 'mixed'")
    attachments: List[MessageAttachment] = Field(
        default_factory=list,
        description="List of attachments (images, files, etc.)"
    )
