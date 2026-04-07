from pydantic import BaseModel, Field


class GoogleApiSettings(BaseModel):
    """Settings for Google API integrations"""
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    webhook_url: str = Field(default="")
    service_account_json: str = Field(default="")

__all__ = ["GoogleApiSettings"]
