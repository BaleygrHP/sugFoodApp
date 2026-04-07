from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AiServiceSettings(BaseModel):
    url: str | None = Field(
        default="http://localhost:5556",
        description="Internal URL for uploading files (used within Docker network)"
    )
    production_url: str | None = Field(
        default=None,
        description="External/production URL for accessing media (used in preview URLs). Falls back to 'url' if not set."
    )
    secret_key: str = Field(
        default="secret",
        description="Secret key for authenticating requests to AI service"
    )

    def get_preview_base_url(self) -> str:
        """Get the base URL to use for preview links (external/production URL)"""
        return self.production_url if self.production_url else self.url


__all__ = [
    "AiServiceSettings"
]
