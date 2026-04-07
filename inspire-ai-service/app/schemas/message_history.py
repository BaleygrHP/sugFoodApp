from pydantic import BaseModel, Field


class SyncMessageHistoryDto(BaseModel):
    """Schema for triggering message history sync for multiple sources"""

    source_ids: list[str] = Field(
        ..., description="IDs of the data sources to sync"
    )
    batch_size: int = Field(
        100, description="Number of messages to process in each batch"
    )
    max_batches: int | None = Field(
        None, description="Maximum number of batches to process (None for all)"
    )
