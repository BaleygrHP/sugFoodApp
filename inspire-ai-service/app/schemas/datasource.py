from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FileSelection(BaseModel):
    """Information about selected Google Drive files"""
    file_id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="MIME type of the file")
    icon_link: Optional[str] = Field(None, description="Icon link for the file")
    web_view_link: Optional[str] = Field(None, description="Web view link for the file")


class GoogleDriveCredentials(BaseModel):
    """Credentials for Google Drive authentication"""
    access_token: str = Field(..., description="OAuth access token for Google Drive API")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")


class GoogleDriveConfig(BaseModel):
    """Configuration for Google Drive import"""
    include_paths: Optional[List[str]] = Field(
        None,
        description="File IDs or folder IDs to include from Google Drive"
    )
    recursive: bool = Field(
        False,
        description="Whether to recursively process folders"
    )
    process_folders: bool = Field(
        True,
        description="Whether to process folders or only individual files"
    )
    chunk_size: Optional[int] = Field(
        None,
        description="Custom chunk size for document indexing"
    )
    chunk_overlap: Optional[int] = Field(
        None,
        description="Custom chunk overlap for document indexing"
    )


class GoogleDriveData(BaseModel):
    """Schema for Google Drive datasource"""
    credentials: GoogleDriveCredentials = Field(..., description="Google Drive credentials")
    config: GoogleDriveConfig = Field(default_factory=GoogleDriveConfig, description="Import configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata to store")
    interval: Optional[str] = Field(None, description="Reindex interval (ONCE, DAILY, WEEKLY, MONTHLY)")

# For backward compatibility
DatasourceData = GoogleDriveData
