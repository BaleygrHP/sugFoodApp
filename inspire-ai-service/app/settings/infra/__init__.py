from pydantic import Field
from pydantic_settings import BaseSettings

from .file_storage import FileStorageSettings
from .google_api import GoogleApiSettings
from .task_queue import TaskQueueSettings
from .vector_store import VectorStoreSettings


class InfraSettings(BaseSettings):
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    file_storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
    task_queue: TaskQueueSettings = Field(default_factory=TaskQueueSettings)
    google_api: GoogleApiSettings = Field(default_factory=GoogleApiSettings)

__all__ = [
    "InfraSettings"
]
