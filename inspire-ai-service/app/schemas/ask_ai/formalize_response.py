"""Schemas for the chat app."""
from typing import Optional
from pydantic import BaseModel, Field

# Define the schemas below

class FormalizeResponseDto(BaseModel):
    """Schema for formalizing a response."""
    text: str
    context: dict[str, str] = {}
    doc_ids: Optional[list[str]] = Field(
        None, description="Optional document IDs to filter by"
    )
