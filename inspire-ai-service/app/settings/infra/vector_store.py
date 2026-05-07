from enum import StrEnum

from pydantic import BaseModel, Field


class VectorStoreType(StrEnum):
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    PINECONE = "pinecone"


class VectorStoreSettings(BaseModel):
    type: VectorStoreType = Field(default=VectorStoreType.QDRANT)
    url: str = Field(default="")
    api_key: str = Field(default="")
    collection: str = Field(default="jarvis-helpdesk-agentic")
    vector_size: int = Field(default=1536)
