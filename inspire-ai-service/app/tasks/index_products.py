from app.lib.constants.source_type import SourceStatusEnum
from app.services.datasource.document import DocumentService
from app.tasks import celery, logger
from app.core.index_manager import get_index_manager
from app.schemas.knowledge import ProductItemDto
from app.lib.constants.platform import Platform, ProductMetadata

@celery.task(name="index_product")
def index_products(items: list[dict], platform: str):
    """Index products into the vector store"""

    try:
        # Convert dict to DTO
        product_items = [ProductItemDto(**item) for item in items]
        platform_enum = Platform(platform)
        index_manager = get_index_manager()

        doc_ids = []
        for item in product_items:
            document = DocumentService.convert_product_to_document(item, platform_enum)
            if not document:
                continue
            _ = index_manager.create_index([document])
            doc_ids.append(document.id_)

            # Callback to AI service removed - no longer needed

        return {
            "status": SourceStatusEnum.INDEXED,
            "refDocIds": [document.id_],
            "error": None
        }


    except Exception as e:
        logger.error(f"Error indexing products: {str(e)}")
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": doc_ids
        }
