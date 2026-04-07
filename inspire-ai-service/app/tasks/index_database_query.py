from typing import Optional
import json

from app.services.datasource.database_query import DatabaseQueryService
from app.core.index_manager import get_index_manager
from app.lib.constants.source_type import SourceStatusEnum

from . import celery, logger


@celery.task(name="index_database_query")
def index_database_query(query: str, uri: str, metadata: Optional[dict] = None, docIds: Optional[list[str]] = None):
    """Index data from a database query"""
    metadata = metadata or {}
    index_manager = get_index_manager()

    try:
        # documents = WebService.load_from_url(web_url)
        documents = DatabaseQueryService.load_from_query(query, uri)

        if not documents:
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": "Could not extract content from URL",
                "refDocIds": [],
            }

        for doc in documents:
            doc.metadata.update({
                **metadata,
                "query": query,
                "uri": uri,
            })

        _ = index_manager.create_index(documents)
        doc_ids = [doc.id_ for doc in documents]

        if docIds:
            index_manager.delete_document(docIds)

        # Callback to AI service removed - no longer needed

        return {"status": SourceStatusEnum.INDEXED, "refDocIds": doc_ids, "error": None}

    except Exception as e:
        logger.error(f"Error indexing Database Query: {str(e)}")
        # Callback to AI service removed - no longer needed
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": [],
        }
