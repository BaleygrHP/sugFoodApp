from pydantic import BaseModel, Field


class LlmIndexSettings(BaseModel):
    chunk_size: int = Field(default=1024)
    chunk_overlap: int = Field(default=20)
