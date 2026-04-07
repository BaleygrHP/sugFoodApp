from typing import Optional

from app.services.datasource.web import WebService
from app.core.index_manager import get_index_manager
from app.lib.constants.source_type import SourceStatusEnum

from . import celery, logger


@celery.task(name="index_single_page")
def index_single_page(web_url: str, docIds: Optional[list[str]] = None, metadata: Optional[dict] = None):
    """Index content from a web URL"""
    metadata = metadata or {}
    index_manager = get_index_manager()

    try:
        documents = WebService.load_from_url(web_url)
        if not documents:
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": "Could not extract content from URL",
                "refDocIds": [],
            }

        for doc in documents:
            doc.metadata.update({
                **metadata,
                "web_url": web_url,
            })

        _ = index_manager.create_index(documents)
        doc_ids = [doc.id_ for doc in documents]

        source_id = metadata.get("sourceId")
        logger.info(f"Source ID: {source_id}")

        if docIds:
            index_manager.delete_document(docIds)

        # Callback to AI service removed - no longer needed

        return {"status": SourceStatusEnum.INDEXED, "refDocIds": doc_ids, "error": None}

    except Exception as e:
        logger.error(f"Error indexing URL {web_url}: {str(e)}")
        # Callback to AI service removed - no longer needed
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": [],
        }


@celery.task(name="index_whole_website")
def index_whole_website(
    tenant_id: str,
    web_url: str,
    max_pages: int = 50,
    max_depth: int = 2,
    interval: str = "DAILY",
    metadata: Optional[dict] = None
):
    """
    Crawl and index an entire website, creating records for discovered pages.
    Processes documents individually for better load distribution.

    Args:
        web_url: The base URL to crawl
        max_pages: Maximum number of pages to crawl (max 100)
        max_depth: Maximum crawling depth
        interval: Crawling interval (DAILY, WEEKLY, etc.)
        metadata: Additional metadata for the documents

    Returns:
        Dict with status, refDocIds, error, and pages_indexed information
    """
    metadata = metadata or {}

    # Validate parameters
    if max_pages > 100:
        logger.warning(f"max_pages={max_pages} exceeds limit of 100, setting to 100")
        max_pages = 100

    index_manager = get_index_manager()
    logger.info(f"Starting whole website indexing for {web_url} (max_pages={max_pages})")

    successful_doc_ids = []
    failed_count = 0

    def process_document(doc, page_number, total_pages):
        """Callback to process each document as it's loaded"""
        nonlocal successful_doc_ids, failed_count
        try:
            # Update document metadata
            doc.metadata.update({
                **metadata,
                "web_url": doc.metadata.get("url", web_url),
                "is_recursive": True,
            })

            # Create index for single document
            index_manager.create_index([doc])
            successful_doc_ids.append(doc.id_)

            # Callback to AI service removed - no longer needed
            logger.info(f"Successfully processed and indexed document {page_number}/{total_pages}")

        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to process document {page_number}/{total_pages}: {str(e)}")

    try:
        # Load and process documents with immediate processing
        documents = WebService.load_from_url(
            web_url,
            is_recursive=True,
            max_pages=max_pages,
            max_depth=max_depth,
            process_callback=process_document
        )

        if not documents:
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": "Could not extract content from website",
                "refDocIds": [],
                "pages_indexed": 0
            }

        # Final summary
        success_count = len(successful_doc_ids)
        logger.info(f"Website indexing completed: {success_count} successful, {failed_count} failed")

        if success_count > 0:
            return {
                "status": SourceStatusEnum.INDEXED,
                "refDocIds": successful_doc_ids,
                "error": None,
                "pages_indexed": success_count,
                "pages_failed": failed_count
            }
        else:
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": f"All {len(documents)} documents failed to process",
                "refDocIds": [],
                "pages_indexed": 0,
                "pages_failed": failed_count
            }

    except Exception as e:
        logger.error(f"Error indexing website {web_url}: {str(e)}")
        # Callback to AI service removed - no longer needed
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": [],
            "pages_indexed": 0
        }
