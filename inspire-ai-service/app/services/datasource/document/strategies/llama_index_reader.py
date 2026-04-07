import os
from pathlib import Path
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader
from app.core.logger import logger
from app.services.datasource.document.strategies.base import DocumentConversionStrategy

class LLamaIndexReaderStrategy(DocumentConversionStrategy):
    """Strategy for files that can be handled by LlamaIndex's built-in loaders"""

    def convert(self, file_path: str, metadata: dict = {}) -> list[Document]:
        """
        Load documents from a file using SimpleDirectoryReader

        Args:
            file_path: Path to the file
            metadata: Additional metadata to attach to documents

        Returns:
            List of Document objects
        """
        documents = []
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            try:
                documents = SimpleDirectoryReader(
                    input_files=[file_path],
                    recursive=False
                ).load_data()

                if documents:
                    logger.info(f"Successfully loaded {len(documents)} documents from {file_path}")
            except Exception as reader_error:
                logger.warning(f"SimpleDirectoryReader failed: {str(reader_error)}")

            # Fallback to text reading if no documents were loaded
            if not documents and os.path.isfile(file_path):
                fallback_docs, success = self._try_text_fallback(file_path)

                if success:
                    documents = fallback_docs

            # Update metadata for all documents
            for doc in documents:
                doc.metadata.update(metadata)

        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise

        return documents

    def _try_text_fallback(self, file_path: str) -> tuple[list[Document], bool]:
        """
        Try to read file as text with different encodings

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (documents list, success boolean)
        """
        # Try these encodings in order
        encodings = ['utf-8', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    documents = [Document(text=content)]
                    logger.info(f"Successfully read file with {encoding} encoding")
                    return documents, True
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading with {encoding} encoding: {str(e)}")
                break

        logger.error("Failed to read file as text with any encoding")
        return [], False
