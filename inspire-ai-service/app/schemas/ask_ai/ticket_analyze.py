"""Schemas for the chat app."""
from typing import Optional
from pydantic import BaseModel, Field

# Define the schemas below

class TicketAnalyzeDto(BaseModel):
    """Schema for ticket analyze."""
    language: Optional[str] = Field(
        None, description="The content of ticket analyze will be written in this language"
    )
    conversation: list[str]

class TicketAnalyzeResponse(BaseModel):
    """Schema response for ticket analyze."""
    summary: str
    tone: str
    satisfaction: str
    purchasing_potential: str
    reason: str
    agent_tone: str
    urgency: str
