from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings

from .gemini import GeminiSettings
from .index import LlmIndexSettings
from .openai import OpenAiSettings


class Provider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"


class LlmSettings(BaseSettings):
    provider: Provider = Field(default=Provider.GEMINI.value)
    index: LlmIndexSettings = Field(default_factory=LlmIndexSettings)
    max_history_messages: int = Field(default=10, description="Max number of most recent chat messages (all roles) to include in prompts")

    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    agentic_gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    ocr_gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    openai: OpenAiSettings = Field(default_factory=OpenAiSettings)


__all__ = [
    "LlmSettings",
    "Provider",
]
