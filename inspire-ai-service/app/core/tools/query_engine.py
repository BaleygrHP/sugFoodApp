from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank, SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import (ResponseMode,
                                                    get_response_synthesizer)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.tools import FunctionTool
from llama_index.core.vector_stores import (FilterOperator, MetadataFilter,
                                            MetadataFilters)
from llama_index.core.prompts import PromptTemplate

from app.core.index_manager import get_index_manager
from app.core.logger import get_logger

logger = get_logger(__name__)


class QueryEngine:
    """Query engine for searching across knowledge bases with optional filtering"""

    def __init__(self):
        self.doc_filter = None
        self.index_manager = get_index_manager()

        # Default configuration
        self.config = {
            "similarity_top_k": 5,
            "similarity_cutoff": 0.3,
            "response_mode": ResponseMode.COMPACT,
            "rerank_top_n": 5,
        }

    def get_config(self) -> dict:
        """Get current engine configuration"""
        return self.config.copy()

    def set_config(self, new_config: dict) -> None:
        """Update engine configuration"""
        self.config.update(new_config)

    def query(self, query_text: str, top_k: int = 5, extract_full: bool = True) -> dict:
        """
        Query across knowledge bases with optional filtering

        Args:
            query_text: The query text
            top_k: Number of results to return
            extract_full: Whether to extract full text for sources

        Returns:
            Dictionary with query results and sources
        """
        try:
            logger.info(f"[QueryEngine] API Request - Query: '{query_text}', top_k: {top_k}, extract_full: {extract_full}")

            if self.doc_filter:
                logger.info(f"[QueryEngine] Using filter with {len(self.doc_filter)} documents: {self.doc_filter[:5]}...")

            vector_index = self.index_manager.load_index()
            query_engine = self.create_query_engine(
                vector_index,
                top_k=top_k,
                response_mode=self.config["response_mode"]
            )

            # Log query engine configuration
            logger.info(f"[QueryEngine] Query engine config - similarity_top_k: {self.config['similarity_top_k']}, similarity_cutoff: {self.config['similarity_cutoff']}")

            # Execute the query with better error handling
            try:
                logger.info(f"[QueryEngine] Executing query with top_k={top_k}, similarity_cutoff={self.config['similarity_cutoff']}")
                response = query_engine.query(query_text)
                logger.info(f"[QueryEngine] Query completed successfully")
            except Exception as template_error:
                logger.error(f"[QueryEngine] Error during template processing: {str(template_error)}")
                # Fall back to a simpler response mode if template error occurs
                backup_query_engine = self.create_query_engine(
                    vector_index,
                    top_k=top_k,
                    response_mode=ResponseMode.COMPACT
                )
                response = backup_query_engine.query(query_text)
                logger.info(f"[QueryEngine] Using fallback query engine with response: {response}")

            sources = self._extract_sources_from_response(response, extract_full)

            if not sources:
                logger.warning(f"[QueryEngine] No documents found for query: '{query_text}'")
            else:
                logger.info(f"[QueryEngine] Found {len(sources)} documents for query")

            # Ensure we return a valid answer
            answer = str(response)
            if not answer or answer.strip() == "":
                answer = "I could not generate a specific answer based on the available information."

            # Log the query answer and sources for debugging
            logger.info(f"[QueryEngine] API Response - Answer length: {len(answer)}")
            logger.info(f"[QueryEngine] API Response - Sources count: {len(sources)}")
            if sources:
                for i, source in enumerate(sources[:3]):  # Log first 3 sources
                    source_id = source.get('id', 'unknown')
                    score = source.get('score', 0.0)
                    logger.info(f"[QueryEngine] API Response - Source {i}: id={source_id}, score={score}")

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error in knowledge query: {str(e)}")
            return {
                "answer": "I encountered an error processing your query. Please try rephrasing or asking a different question.",
                "sources": [],
            }

    async def aquery(self, query_text: str, top_k: int = 5, extract_full: bool = True) -> dict:
        """
        Async version of query method for parallel execution

        Args:
            query_text: The query text
            top_k: Number of results to return
            extract_full: Whether to extract full text for sources

        Returns:
            Dictionary with query results and sources
        """
        try:
            logger.info(f"[QueryEngine] API Request - Async Query: '{query_text}', top_k: {top_k}, extract_full: {extract_full}")

            if self.doc_filter:
                logger.info(f"[QueryEngine] Using filter with {len(self.doc_filter)} documents: {self.doc_filter[:5]}...")

            vector_index = self.index_manager.load_index()

            # Debug: Check index status
            try:
                if hasattr(vector_index, 'docstore') and hasattr(vector_index.docstore, 'get_all_document_ids'):
                    doc_ids = vector_index.docstore.get_all_document_ids()
                    logger.info(f"[QueryEngine] Index contains {len(doc_ids)} documents")
                    if len(doc_ids) > 0:
                        logger.info(f"[QueryEngine] Sample document IDs: {list(doc_ids)[:5]}")
                else:
                    logger.warning(f"[QueryEngine] Cannot determine document count in index")
            except Exception as e:
                logger.warning(f"[QueryEngine] Error checking index status: {e}")

            query_engine = self.create_query_engine(
                vector_index,
                top_k=top_k,
                response_mode=self.config["response_mode"]
            )

            # Log query engine configuration
            logger.info(f"[QueryEngine] Query engine config - similarity_top_k: {self.config['similarity_top_k']}, similarity_cutoff: {self.config['similarity_cutoff']}")

            # Execute the query with better error handling
            try:
                logger.info(f"[QueryEngine] Starting async query with top_k={top_k}, similarity_cutoff={self.config['similarity_cutoff']}")

                # Debug: Test retriever directly
                try:
                    retriever = query_engine.retriever
                    retrieved_nodes = retriever.retrieve(query_text)
                    logger.info(f"[QueryEngine] Retriever found {len(retrieved_nodes)} nodes before postprocessing")
                    for i, node in enumerate(retrieved_nodes[:3]):
                        score = getattr(node, 'score', 'N/A')
                        logger.info(f"[QueryEngine] Retrieved node {i}: score={score}, id={getattr(node.node, 'id_', 'N/A')}")
                except Exception as retriever_error:
                    logger.warning(f"[QueryEngine] Error testing retriever: {retriever_error}")

                response = await query_engine.aquery(query_text)
                logger.info(f"[QueryEngine] Async query completed successfully")
                logger.info(f"[QueryEngine] Query response type: {type(response)}, content length: {len(str(response))}")
            except Exception as template_error:
                logger.error(f"[QueryEngine] Error during template processing: {str(template_error)}")
                # Fall back to a simpler response mode if template error occurs
                backup_query_engine = self.create_query_engine(
                    vector_index,
                    top_k=top_k,
                    response_mode=ResponseMode.COMPACT
                )
                response = await backup_query_engine.aquery(query_text)
                logger.info(f"[QueryEngine] Using fallback query engine with response: {response}")

            sources = self._extract_sources_from_response(response, extract_full)

            # Debug: Check if response has source nodes
            if hasattr(response, 'source_nodes'):
                logger.info(f"[QueryEngine] Response has {len(response.source_nodes)} source nodes")
                for i, node in enumerate(response.source_nodes[:3]):  # Log first 3 nodes
                    logger.info(f"[QueryEngine] Source node {i}: score={getattr(node, 'score', 'N/A')}, id={getattr(node.node, 'id_', 'N/A')}")
            else:
                logger.warning(f"[QueryEngine] Response has no source_nodes attribute")

            if not sources:
                logger.warning(f"[QueryEngine] No documents found for query: '{query_text}'")
                logger.info(f"[QueryEngine] Query config: similarity_cutoff={self.config['similarity_cutoff']}, top_k={top_k}")
                if self.doc_filter:
                    logger.info(f"[QueryEngine] Document filter active with {len(self.doc_filter)} docs: {self.doc_filter[:5]}")
                else:
                    logger.info(f"[QueryEngine] No document filter - searching all documents")
            else:
                logger.info(f"[QueryEngine] Found {len(sources)} documents for query")

            # Ensure we return a valid answer
            answer = str(response)
            if not answer or answer.strip() == "":
                answer = "I could not generate a specific answer based on the available information."

            # Log the query answer and sources for debugging
            logger.info(f"[QueryEngine] API Response - Answer length: {len(answer)}")
            logger.info(f"[QueryEngine] API Response - Sources count: {len(sources)}")
            if sources:
                for i, source in enumerate(sources[:3]):  # Log first 3 sources
                    source_id = source.get('id', 'unknown')
                    score = source.get('score', 0.0)
                    logger.info(f"[QueryEngine] API Response - Source {i}: id={source_id}, score={score}")

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error in async knowledge query: {str(e)}")
            return {
                "answer": "I encountered an error processing your query. Please try rephrasing or asking a different question.",
                "sources": [],
            }

    def create_query_engine(
        self,
        index: VectorStoreIndex,
        top_k: int = None,
        response_mode: str = None,
    ) -> RetrieverQueryEngine:
        """
        Create a query engine with integrated retriever

        Args:
            index: Vector store index
            top_k: Number of results to return
            response_mode: Response synthesis mode

        Returns:
            RetrieverQueryEngine instance
        """
        similarity_top_k = self.config["similarity_top_k"]
        rerank_top_n = top_k or self.config["rerank_top_n"]
        response_mode = response_mode or self.config["response_mode"]
        similarity_cutoff = self.config["similarity_cutoff"]


        metadata_filters = None
        if self.doc_filter:
            metadata_filters = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="document_id",
                        value=self.doc_filter,
                        operator=FilterOperator.IN,
                    )
                ]
            )

        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k,
            filters=metadata_filters,
        )

        # Define a custom QA template using the PromptTemplate class
        qa_template = PromptTemplate(
            template="""Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query. If the context doesn't contain the answer, synthesize a helpful response based on what information is available.
Query: {query_str}
Answer: """
        )

        # Configure response synthesizer with improved parameters
        response_synthesizer = get_response_synthesizer(
            response_mode=response_mode,
            use_async=False,
            text_qa_template=qa_template
        )

        postprocessors = [
            SimilarityPostprocessor(
                similarity_cutoff=similarity_cutoff,
                filter_empty=True,
                filter_duplicates=True,
                filter_similar=True,
            ),
            LLMRerank(top_n=rerank_top_n, choice_batch_size=similarity_top_k),
        ]

        return RetrieverQueryEngine(
            retriever=retriever,
            node_postprocessors=postprocessors,
            response_synthesizer=response_synthesizer,
        )

    def _extract_sources_from_response(self, response: any, extract_full: bool = True) -> list[dict]:
        """
        Extract and format sources from response

        Args:
            response: Query response

        Returns:
            List of formatted sources
        """
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:

                if hasattr(node.node, 'get_content'):
                    text = node.node.get_content()
                elif hasattr(node.node, 'content'):
                    text = node.node.content
                elif hasattr(node.node, 'text'):
                    text = node.node.text
                else:
                    text = str(node.node)

                source = {
                    "id": node.node.id_,
                    "text": (
                        text
                        if extract_full
                        else text[:100] + "..." if len(text) > 100 else text
                    ),
                    "score": getattr(node, "score", 0.0),
                    "metadata": {
                        k: v
                        for k, v in node.node.metadata.items()
                        if k in ["file_name", "file_path", "web_url", "source_id"]
                    },
                }
                sources.append(source)
        return sources

    def set_doc_filter(self, doc_ids: list[str]) -> None:
        self.doc_filter = doc_ids

    def clear_doc_filter(self) -> None:
        self.doc_filter = None

    def create_tool(self, name: str, description: str, top_k: int = 5) -> FunctionTool:
        """
        Create a query tool for the agent to use

        Returns:
            FunctionTool for knowledge query
        """
        if self.doc_filter:
            logger.info(f"Using filter with {len(self.doc_filter)} documents: {self.doc_filter[:5]}...")

        return FunctionTool.from_defaults(
            self.query,
            name=name,
            description=description,
            partial_params={"top_k": top_k, "extract_full": True}
        )

def get_query_engine() -> QueryEngine:
    return QueryEngine()
