from enum import StrEnum

from pydantic import BaseModel, Field


class FileStorageType(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class FileStorageSettings(BaseModel):
    type: FileStorageType = Field(default=FileStorageType.LOCAL)
    data_dir: str = Field(default="data")
    static_dir: str = Field(default="static")
