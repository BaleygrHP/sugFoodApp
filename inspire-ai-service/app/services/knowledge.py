from fastapi import UploadFile
from typing import Dict, Any

from app.core.logger import get_logger
from app.lib.constants.platform import Platform
from app.lib.constants.source_type import SourceStatusEnum
from app.schemas.datasource import GoogleDriveData
from app.services.datasource.database_query import DatabaseQueryService
from app.services.file_storage import get_file_storage
from app.settings import settings
from app.tasks import index_local_file, index_google_drive, index_products, index_single_page, index_whole_website, index_database_query
from app.schemas.knowledge import ProductItemDto

logger = get_logger(__name__)


class KnowledgeService:
    def __init__(self):
        self.file_storage = get_file_storage(settings.infra.file_storage)

    async def import_local_file(self, file: UploadFile, metadata: dict = None):
        """
        Import a local file into the vector store

        Args:
            file: The uploaded file
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        metadata = metadata or {}
        file_path = None

        try:
            file_path = await self.file_storage.save_file(file, directory="knowledge")
            if not file_path or not self.file_storage.file_exists(file_path):
                return {
                    "filePath": None,
                    "status": SourceStatusEnum.LOADED_FAILED,
                    "metadata": {
                        "error": "File not found after saved",
                    },
                }

            # Index directly (no Celery worker)
            result = index_local_file(file_path, file.filename, metadata)

            return {
                "filePath": file_path,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.exception(f"Error importing file {file.filename}: {str(e)}")
            return {
                "filePath": file_path,
                "status": SourceStatusEnum.LOADED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def import_products(self, items: list[ProductItemDto], platform: Platform):
        """
        Import products into the vector store
        """

        items_dict = []
        for item in items:
            item_dict = item.model_dump()
            items_dict.append(item_dict)

        # Index directly (no Celery worker)
        result = index_products(items_dict, platform.value)

        return {
            "status": result.get("status", SourceStatusEnum.INDEXED),
            "refDocIds": result.get("refDocIds", []),
            "error": result.get("error"),
        }

    def import_web(self, web_url: str, metadata: dict = None):
        """
        Import content from a web URL into the vector store

        Args:
            web_url: URL to import content from
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        metadata = metadata or {}

        try:
            # Index directly (no Celery worker)
            result = index_single_page(web_url, metadata=metadata)

            return {
                "webUrl": web_url,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "webUrl": web_url,
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }
    def import_whole_sites(self, tenant_id: str, web_url: str, metadata: dict = None, max_pages: int = 1):
        """
        Import content from a web URL into the vector store

        Args:
            tenant_id: Tenant ID
            web_url: URL to import content from
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        metadata = metadata or {}

        try:
            # Index directly (no Celery worker)
            result = index_whole_website(tenant_id, web_url, metadata=metadata, max_pages=max_pages)

            return {
                "webUrl": web_url,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "pages_indexed": result.get("pages_indexed", 0),
                "pages_failed": result.get("pages_failed", 0),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "webUrl": web_url,
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def delete_documents(self, doc_ids: list[str], file_paths: list[str] | None = None):
        """
        Delete documents from the vector store and optionally delete the associated file.

        Args:
            doc_ids: List of document IDs to delete.
            file_path: Path to the file to delete from storage (optional).

        Returns:
            Dict with the results of the deletion process for documents and file.
        """
        from app.core.index_manager import get_index_manager
        index_manager = get_index_manager()
        results = {
            "documents_deleted": [],
            "documents_failed": [],
            "files_deleted": [],
            "files_failed": [],
        }
        for doc_id in doc_ids:
            result = index_manager.delete_document([doc_id])
            if result:
                results["documents_deleted"].append(doc_id)
            else:
                results["documents_failed"].append(doc_id)

        if file_paths is not None:
            for file_path in file_paths:
                file_deleted = self.file_storage.delete_file(file_path)
                if file_deleted:
                    results["files_deleted"].append(file_path)
                else:
                    results["files_failed"].append(file_path)

        return results

    def reindex_web(self, web_url: str, previous_doc_ids: list[str], metadata: dict = None):
        """
        Re-index content from a web URL into the vector store

        Args:
            web_url: URL to import content from
            previous_doc_ids: Document ids resulted from the latest indexing process
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        metadata = metadata or {}

        try:
            # Index directly (no Celery worker)
            result = index_single_page(web_url=web_url, docIds=previous_doc_ids, metadata=metadata)

            return {
                "webUrl": web_url,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "webUrl": web_url,
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def import_google_drive(self, google_drive_data: GoogleDriveData):
        """
        Import content from Google Drive into the vector store

        Args:
            google_drive_data: Dictionary containing Google Drive configuration and credentials

        Returns:
            Dict with metadata about the imported content
        """
        try:
            # Index directly (no Celery worker)
            result = index_google_drive(google_drive_data.model_dump())

            return {
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Error importing from Google Drive: {str(e)}")
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def get_latest_revision(self, file_id: str, credentials: dict):
        """
        Get the latest revision of a Google Drive file and check if it's new

        Args:
            file_id: The Google Drive file ID
            credentials: Dict containing access_token and refresh_token

        Returns:
            Dict containing:
            - hasNewRevision: bool
            - revision: str (if hasNewRevision is True)
            - newAccessToken: str (if token was refreshed)
        """
        try:
            from app.services.datasource.google_drive import GoogleDriveClient

            # Initialize drive client
            drive_client = GoogleDriveClient({
                "access_token": credentials['accessToken'],
                "refresh_token": credentials['refreshToken']
            })

            if not drive_client.authenticate():
                raise Exception("Failed to authenticate with Google Drive")

            # Get file revisions
            revisions = drive_client.get_file_revisions(file_id)

            if not revisions:
                return {
                    "revision": None,
                }

            latest_revision = revisions[-1]  # Google Drive returns revisions in descending order

            return {
                "revision": latest_revision['id']
            }

        except Exception as e:
            logger.error(f"Error getting latest revision: {str(e)}")
            raise

    def import_database_query(self, query: str, uri: str, metadata: dict = None):
        """
        Import data from database using a query into vector store.

        Args:
            query: SQL Query to select data
            uri: Database URI
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        try:
            # Index directly (no Celery worker)
            result = index_database_query(query=query, uri=uri, metadata=metadata)

            return {
                "query": query,
                "uri": uri,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "query": query,
                "uri": uri,
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def reindex_database_query(self, query: str, uri: str, previous_doc_ids: list[str], metadata: dict = None):
        """
        Import data from database using a query into vector store.

        Args:
            query: SQL Query to select data
            uri: Database URI
            metadata: Additional metadata to store with the document (optional)

        Returns:
            Dict with metadata about the imported content
        """
        try:
            # Index directly (no Celery worker)
            result = index_database_query(query=query, uri=uri, metadata=metadata, docIds=previous_doc_ids)

            return {
                "query": query,
                "uri": uri,
                "status": result.get("status", SourceStatusEnum.INDEXED),
                "refDocIds": result.get("refDocIds", []),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "query": query,
                "uri": uri,
                "status": SourceStatusEnum.INDEXED_FAILED,
                "metadata": {
                    "error": str(e),
                },
            }

    def test_database_query(self, query: str, uri: str):
        """
        Test database connection and query.

        Args:
            query: SQL Query to select data
            uri: Database URI

        Returns:
            Rows from query.
        """
        return DatabaseQueryService.test_connection(query, uri)
