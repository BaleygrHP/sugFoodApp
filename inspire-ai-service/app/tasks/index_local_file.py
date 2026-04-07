import mimetypes
from typing import Optional

from app.core.index_manager import get_index_manager
from app.lib.constants.source_type import SourceStatusEnum
from app.lib.utils.file import FileUtils
from app.services.datasource.document import DocumentService
from app.tasks import celery, logger


@celery.task(name="index_local_file")
def index_local_file(file_path: str, file_name: str, metadata: Optional[dict] = None):
    """Index content from a local file"""
    metadata = metadata or {}
    metadata["original_file_name"] = file_name

    try:
        mime_type = mimetypes.guess_type(file_name)[0] or ""
        if FileUtils.get_document_type(mime_type) != "document":
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": "File is not a document",
                "refDocIds": [],
            }

        documents = DocumentService.convert_file_to_documents(file_path, file_name, metadata)
        if not documents:
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": "Could not extract content from file",
                "refDocIds": [],
            }

        index_manager = get_index_manager()
        _ = index_manager.create_index(documents)
        doc_ids = [doc.id_ for doc in documents]

        # Callback to AI service removed - no longer needed

        return {"status": SourceStatusEnum.INDEXED, "refDocIds": doc_ids, "error": None}

    except Exception as e:
        logger.error(f"Error indexing file {file_path}: {str(e)}")
        # Callback to AI service removed - no longer needed
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": [],
        }
