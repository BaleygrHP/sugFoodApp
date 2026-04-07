from abc import ABC, abstractmethod

from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.core.storage import StorageContext

from app.core.logger import get_logger
from app.settings import settings
from app.settings.infra.vector_store import VectorStoreSettings, VectorStoreType

logger = get_logger(__name__)


class VectorStoreAdapter(ABC):
    @abstractmethod
    def initialize(self, settings) -> None:
        pass

    @abstractmethod
    def delete_document(self, doc_ids: str | list[str]) -> bool:
        pass

    @abstractmethod
    def load_index(self) -> VectorStoreIndex:
        pass

    @abstractmethod
    def create_index(self, documents: list[Document]) -> VectorStoreIndex:
        pass

    @abstractmethod
    def create_index_with_custom_chunking(
        self, documents: list[Document], chunk_size: int = 2500, chunk_overlap: int = 250
    ) -> VectorStoreIndex:
        pass

    @abstractmethod
    def get_vector_store(self):
        pass


class QdrantAdapter(VectorStoreAdapter):
    """Adapter for Qdrant vector store"""

    def initialize(self, settings: VectorStoreSettings) -> None:
        """Initialize the Qdrant vector store adapter with the provided settings"""
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from qdrant_client import AsyncQdrantClient, QdrantClient
        from llama_index.core import Settings as LlamaIndexSettings

        # Get actual embedding dimension from the embed model
        try:
            # Try to get dimension from embed model
            embed_model = LlamaIndexSettings.embed_model
            if hasattr(embed_model, 'dimension'):
                actual_dimension = embed_model.dimension
            elif hasattr(embed_model, 'model_name'):
                # Try to infer from model name
                model_name = str(embed_model.model_name).lower()
                if 'text-embedding-004' in model_name:
                    actual_dimension = 768  # Gemini text-embedding-004
                elif 'text-embedding-ada-002' in model_name or 'text-embedding-3' in model_name:
                    actual_dimension = 1536  # OpenAI embeddings
                else:
                    # Default to settings or try to get from model
                    actual_dimension = settings.vector_size
                    logger.warning(f"Could not determine embedding dimension from model {model_name}, using {actual_dimension}")
            else:
                actual_dimension = settings.vector_size
                logger.warning(f"Could not determine embedding dimension, using configured value: {actual_dimension}")
        except Exception as e:
            logger.warning(f"Error getting embedding dimension: {e}, using configured value: {settings.vector_size}")
            actual_dimension = settings.vector_size

        # Use actual dimension instead of configured one
        vector_size = actual_dimension
        logger.info(f"Using vector dimension: {vector_size}")

        # Extract URL parts
        url = settings.url
        use_https = url.startswith("https://")

        url = url.replace("https://", "") if use_https else url.replace("http://", "")

        if ":" in url:
            host, port = url.split(":")
            port = int(port)
        else:
            host = url
            port = 6333

        # Setup connection params based on URL format
        if use_https or settings.api_key:
            client_kwargs = {
                "url": f"https://{host}" if use_https else f"http://{host}",
            }
            if (port != 443 and use_https) or (port != 80 and not use_https):
                client_kwargs["url"] += f":{port}"
        else:
            client_kwargs = {
                "location": f"{host}:{port}"
            }

        if settings.api_key:
            client_kwargs["api_key"] = settings.api_key

        logger.info(f"Connecting to Qdrant vector store at {host} with collection {settings.collection}")

        # Initialize both sync and async clients
        self.client = QdrantClient(**client_kwargs)
        self.async_client = AsyncQdrantClient(**client_kwargs)

        collection_exists = False
        collection_dimension = None

        try:
            # Check if collection exists and get its dimension
            collection_info = self.client.get_collection(settings.collection)
            collection_exists = True
            # Get vector size from collection config
            vectors_config = collection_info.config.params.vectors
            if hasattr(vectors_config, 'size'):
                collection_dimension = vectors_config.size
            elif hasattr(vectors_config, 'params') and hasattr(vectors_config.params, 'size'):
                collection_dimension = vectors_config.params.size
            else:
                # Try to get from named vectors if it's a named vector config
                if hasattr(vectors_config, 'named'):
                    # Get first named vector dimension
                    named_vectors = vectors_config.named
                    if named_vectors:
                        first_vector = list(named_vectors.values())[0]
                        if hasattr(first_vector, 'size'):
                            collection_dimension = first_vector.size

            logger.info(f"Collection exists with dimension: {collection_dimension}")

            # Check if dimension matches
            if collection_dimension and collection_dimension != vector_size:
                logger.warning(
                    f"Collection dimension mismatch! Collection has {collection_dimension}, "
                    f"but embedding model produces {vector_size}. "
                    f"Deleting and recreating collection..."
                )
                # Delete existing collection
                self.client.delete_collection(settings.collection)
                collection_exists = False

        except Exception as e:
            # Collection doesn't exist or error accessing it
            logger.info(f"Collection does not exist or error accessing it: {str(e)}")
            collection_exists = False

        if not collection_exists:
            # Create collection with correct dimension
            logger.info(f"Creating collection {settings.collection} with dimension {vector_size}")
            self.client.create_collection(
                collection_name=settings.collection,
                vectors_config={
                    "size": vector_size,
                    "distance": "Cosine"
                },
                optimizers_config={
                    "default_segment_number": 2
                }
            )

            # Create payload index for document_id
            self.client.create_payload_index(
                collection_name=settings.collection,
                field_name="document_id",
                field_schema="keyword"
            )

            # Create payload index for doc_id
            self.client.create_payload_index(
                collection_name=settings.collection,
                field_name="doc_id",
                field_schema="keyword"
            )
        else:
            # Collection exists and dimension matches, just ensure payload indexes exist
            try:
                collection_info = self.client.get_collection(settings.collection)
                payload_schema = collection_info.payload_schema or {}
                document_id_indexed = payload_schema.get("document_id", None)
                doc_id_indexed = payload_schema.get("doc_id", None)

                if not document_id_indexed:
                    logger.info(f"Creating payload index for document_id in collection {settings.collection}")
                    self.client.create_payload_index(
                        collection_name=settings.collection,
                        field_name="document_id",
                        field_schema="keyword"
                    )
                else:
                    logger.info(f"Document ID index already exists in collection {settings.collection}")

                if not doc_id_indexed:
                    logger.info(f"Creating payload index for doc_id in collection {settings.collection}")
                    self.client.create_payload_index(
                        collection_name=settings.collection,
                        field_name="doc_id",
                        field_schema="keyword"
                    )
                else:
                    logger.info(f"Doc ID index already exists in collection {settings.collection}")
            except Exception as e:
                logger.warning(f"Error checking/creating payload indexes: {str(e)}")

        self.vector_store = QdrantVectorStore(
            client=self.client,
            aclient=self.async_client,
            collection_name=settings.collection,
            vector_dimension=vector_size,
            batch_size=10,
        )

    def delete_document(self, doc_ids: str | list[str]) -> bool:
        """Delete documents from the vector store"""
        try:
            if isinstance(doc_ids, str):
                self.vector_store.delete(doc_ids)
            elif isinstance(doc_ids, list):
                for doc_id in doc_ids:
                    self.vector_store.delete(doc_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {str(e)}")
            return False

    def load_index(self) -> VectorStoreIndex:
        """Load the index from the vector store"""
        try:
            index = VectorStoreIndex.from_vector_store(self.vector_store)
            if index is None:
                raise Exception("Index not found")
            return index
        except Exception as e:
            logger.error(f"Error loading index from vector store: {str(e)}")
            raise

    def create_index(self, documents: list[Document]) -> VectorStoreIndex:
        """Create an index from the provided documents"""
        try:
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                insert_batch_size=2048,
            )
            return index
        except Exception as e:
            logger.exception(f"Error creating index from documents: {e!s}")
            raise

    def create_index_with_custom_chunking(
        self,
        documents: list[Document],
        chunk_size: int = 2500,
        chunk_overlap: int = 250,
    ) -> VectorStoreIndex:
        """Create an index using the LlamaIndex ingestion pipeline with smart chunking for tabular data"""
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.node_parser import SentenceSplitter
        from app.core.tabular_chunker import TabularNodeParser

        try:
            # Check if we have tabular data
            has_tabular_data = any(
                doc.metadata.get("file_type") == "tabular" or
                doc.metadata.get("file_extension") in [".xlsx", ".xls", ".csv"]
                for doc in documents
            )

            if has_tabular_data:
                # Use specialized tabular chunker for better table structure preservation
                logger.info("Detected tabular data, using specialized chunker")
                node_parser = TabularNodeParser(
                    chunk_size=50,  # Rows per chunk for tabular data
                    chunk_overlap=5,  # Row overlap
                    preserve_headers=True,
                    preserve_ids=True
                )
            else:
                # Use standard sentence splitter for non-tabular data
                node_parser = SentenceSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    paragraph_separator="\n\n",
                )

            pipeline = IngestionPipeline(
                transformations=[node_parser],
                vector_store=self.vector_store,
            )

            nodes = pipeline.run(
                documents=documents,
            )
            logger.info(f"Created {len(nodes)} nodes from {len(documents)} documents")

            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index = VectorStoreIndex(
                nodes=nodes,
                storage_context=storage_context,
            )

            return index
        except Exception as e:
            logger.error(f"Error creating index with chunking: {str(e)}")
            raise

    def get_vector_store(self):
        return self.vector_store


def create_vector_store_adapter(settings: VectorStoreSettings) -> VectorStoreAdapter:
    """Factory function to create a vector store adapter based on settings"""
    if settings.type == VectorStoreType.QDRANT:
        adapter = QdrantAdapter()
    else:
        logger.warning(f"Vector store type {settings.type} not implemented, falling back to Qdrant")
        adapter = QdrantAdapter()

    return adapter


class IndexManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not IndexManager._initialized:
            self.adapter = create_vector_store_adapter(settings.infra.vector_store)
            self.adapter.initialize(settings.infra.vector_store)
            IndexManager._initialized = True

    def _initialize(self):
        self.adapter.initialize(self.settings)

    def delete_document(self, doc_ids):
        return self.adapter.delete_document(doc_ids)

    def create_index(self, documents):
        return self.adapter.create_index(documents)

    def create_index_with_custom_chunking(self, documents, chunk_size=None):
        if chunk_size is None:
            chunk_size = settings.llm.index.chunk_size
        return self.adapter.create_index_with_custom_chunking(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=settings.llm.index.chunk_overlap,
        )

    def load_index(self):
        return self.adapter.load_index()

    def get_vector_store(self):
        return self.adapter.get_vector_store()


def get_index_manager() -> IndexManager:
    if not IndexManager._instance:
        IndexManager._instance = IndexManager()
    return IndexManager._instance
