import os
from pathlib import Path
from llama_index.core.schema import Document

from app.services.datasource.document.strategies import (
    MarkItDownBasicStrategy,
    MarkItDownLLMStrategy,
    LLamaIndexReaderStrategy,
    TabularDataStrategy,
)
from app.schemas.knowledge import ProductItemDto
from app.lib.constants.platform import Platform, ProductMetadata
from app.lib.helpers.office_converter import OfficeConverter
from app.core.logger import get_logger

logger = get_logger(__name__)

class DocumentService:
    _STRATEGIES = {
        ".docx": MarkItDownLLMStrategy(),
        ".pdf": MarkItDownLLMStrategy(),
        ".pptx": MarkItDownBasicStrategy(),
        # Specialized strategy for tabular data
        ".xlsx": TabularDataStrategy(),
        ".xls": TabularDataStrategy(),
        ".csv": TabularDataStrategy(),
        # Generic strategy handles all other supported file types
        "default": LLamaIndexReaderStrategy()
    }

    @staticmethod
    def convert_product_to_document(item: ProductItemDto, platform: Platform) -> Document:
        text = f"""
            {platform} Id: {item.external_id}
            Name: {item.name}
            Description: {item.description}
            Price: {item.price} {item.currency}
            Category: {item.category}
            Brand: {item.brand}
        """

        return Document(text=text, metadata={
                ProductMetadata.SOURCE_ID: item.source_id,
                ProductMetadata.PLATFORM: platform
            })


    @staticmethod
    def _update_documents_metadata(documents: list[Document], metadata: dict = {}) -> list[Document]:
        for doc in documents:
            doc.metadata |= metadata
        return documents

    @staticmethod
    def convert_file_to_documents(
        file_path: str, file_name: str, metadata: dict = {}
    ) -> list[Document]:
        """
        Convert a file to a list of Documents using the appropriate strategy.

        Args:
            file_path (str): Path to the file
            metadata (dict): Additional metadata to attach to the documents

        Returns:
            list[Document]: List of converted documents

        Raises:
            ValueError: If no appropriate strategy is found for the file type
        """
        file_extension = Path(file_path).suffix.lower()

        # Add default metadata
        metadata = {**metadata, "file_path": file_path, "file_extension": file_extension, "file_name": file_name}

        is_legacy_format = file_extension in OfficeConverter.LEGACY_SUPPORTED_FORMATS
        # Convert the file to a modern format if it is a legacy format
        if is_legacy_format:
            file_path = OfficeConverter.convert_to_modern_format(file_path)
            file_extension = Path(file_path).suffix.lower()

        # Get the appropriate strategy or fall back to generic strategy
        strategy = DocumentService._STRATEGIES.get(file_extension, DocumentService._STRATEGIES["default"])

        # Convert the file using the selected strategy
        documents = strategy.convert(file_path, metadata)

        documents = DocumentService._update_documents_metadata(documents, metadata)

        # Delete the converted file
        if is_legacy_format:
            logger.info(f"Deleting converted file: {file_path}")
            os.remove(file_path)

        return documents
