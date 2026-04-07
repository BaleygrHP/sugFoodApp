from enum import StrEnum
from enum import Enum


class SourceType(StrEnum):
    LOCAL_FILE = "file"
    WEB = "web"
    GOOGLE_DRIVE = "google-drive"
    MESSAGE_HISTORY = "message-history"
    DATABASE_QUERY = "database-query"


class SourceStatusEnum(StrEnum):
    LOADED_FAILED = "loaded_failed"
    INDEXED_FAILED = "failed"
    INDEXED = "indexed"
    INDEXING = "indexing"
    ACTIVE = "active"
    INACTIVE = "inactive"
