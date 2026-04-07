from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .infra import InfraSettings
from .llm import LlmSettings
from .ai_service import AiServiceSettings


class Settings(BaseSettings):
    infra: InfraSettings = Field(default_factory=InfraSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    ai_service: AiServiceSettings = Field(default_factory=AiServiceSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()

__all__ = ["Settings", "settings"]
