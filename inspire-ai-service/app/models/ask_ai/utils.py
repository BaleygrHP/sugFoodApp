from pydantic import BaseModel
from app.models.ask_ai.actions import Action
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class Topic(BaseModel):
    """A class represents for a topic of conversation, consists actions for AI agent to perform"""
    topic_name: str
    description: str
    instructions: list[str] = []
    actions: list[Action] = []
    default_topic_code: str | None = None

    def get_tools(self):
        return [action.create_tool() for action in self.actions]


class TicketStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    REQUIRE_REAL_AGENT = "Require Real Agent"

class AgentResponseWithTicketInfo(BaseModel):
    response: str = Field(..., description="Final response/answer")
    status: TicketStatus = Field(TicketStatus.OPEN, description="Conversation status after sending the response/answer")
