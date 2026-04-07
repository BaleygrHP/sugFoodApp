from typing import Optional
from pydantic import BaseModel, Field


class ImportWebDto(BaseModel):
    web_url: str = Field(..., description="URL of the web page")
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata to store with the document"
    )

class ImportWholeSitesWebDto(ImportWebDto):
    tenant_id: str = Field(..., description="Tenant ID")
    is_recursive: Optional[bool] = Field(
        default=False, description="Whether to crawl recursively"
    )
    max_pages: Optional[int] = Field(
        default=1, description="Maximum number of pages to crawl"
    )

class ReindexWebDto(BaseModel):
    web_url: str = Field(..., description="URL of the web page")
    previous_doc_ids: list[str] = Field(..., description="Document ids resulted from the latest indexing process")
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata to store with the document"
    )

class DeleteDocumentsDto(BaseModel):
    ref_doc_ids: list[str]
    file_paths: Optional[list[str]] = Field(
        default=None, description="List of file paths to delete documents from"
    )


class QueryKnowledgeDto(BaseModel):
    query: str = Field(..., description="Question to ask the knowledge base")
    ref_doc_ids: Optional[list[str]] = Field(
        default=None, description="List of document IDs to filter the search (optional)"
    )
    top_k: Optional[int] = Field(
        default=5, description="Number of most relevant documents to consider"
    )


class ProductItemDto(BaseModel):
    """Schema for product item"""
    external_id: Optional[str] = Field(None, description="External ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: Optional[float] = Field(None, description="Product price")
    currency: Optional[str] = Field(None, description="Product currency")
    category: Optional[str] = Field(None, description="Product category")
    source_id: str = Field(..., description="Source ID")
    brand: Optional[str] = Field(None, description="Product brand")

class ImportProductsDto(BaseModel):
    """Schema for product datasource"""
    items: list[ProductItemDto] = Field(default_factory=list, description="List of product items")
    platform: str = Field(..., description="Platform name", examples=['lazada'])
class GetLatestRevisionDto(BaseModel):
    file_id: str = Field(..., description="The Google Drive file ID to get revision for")
    access_token: str = Field(..., description="Google Drive access token")
    refresh_token: str = Field(..., description="Google Drive refresh token")


class ImportDatabaseQueryDto(BaseModel):
    """Schema for Database Query"""
    query: str = Field(..., description="SQL Query")
    uri: str = Field(..., description="Database URI")
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata to store with the document"
    )

class ReindexDatabaseQueryDto(BaseModel):
    """Schema for Reindexing Database Query"""
    query: str = Field(..., description="SQL Query")
    uri: str = Field(..., description="Database URI")
    previous_doc_ids: list[str] = Field(..., description="Document ids resulted from the latest indexing process")
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata to store with the document"
    )
