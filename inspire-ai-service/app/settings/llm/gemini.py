from pydantic import BaseModel, Field


class GeminiSettings(BaseModel):
    api_key: str | None = Field(default=None)
    model_name: str | None = Field(default=None)
    embed_model: str | None = Field(default=None)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=8192)
    tool_execution_temperature: float = Field(
        default=0.0,
        description="Temperature for tool-using agents. Set to 0.0 for deterministic tool execution."
    )
