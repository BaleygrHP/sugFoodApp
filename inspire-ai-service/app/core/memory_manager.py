from llama_index.core import Settings as LlamaIndexSettings
from llama_index.core.llms import LLM
from llama_index.core.memory import (
    BaseMemoryBlock,
    FactExtractionMemoryBlock,
    InsertMethod,
    Memory,
    VectorMemoryBlock,
)

from app.core.index_manager import get_index_manager
from app.core.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    DEFAULT_TOKEN_LIMIT = 30000
    DEFAULT_CHAT_HISTORY_TOKEN_RATIO = 0.7
    DEFAULT_TOKEN_FLUSH_SIZE = 3000
    DEFAULT_INSERT_METHOD = InsertMethod.USER

    def __init__(self, llm: LLM | None = None):
        """Initialize the Memory Manager."""
        self.llm = llm
        self.embed_model = LlamaIndexSettings.embed_model

    def _create_default_memory_blocks(self) -> list[BaseMemoryBlock]:
        """Tạo memory blocks mặc định với cấu hình chung."""
        if self.llm is None:
            return []

        blocks = []

        blocks.append(
            FactExtractionMemoryBlock(
                name="extracted_facts",
                llm=self.llm,
                max_facts=50,
                priority=1,
            )
        )

        blocks.append(
            VectorMemoryBlock(
                name="conversation_history",
                vector_store=get_index_manager().get_vector_store(),
                embed_model=self.embed_model,
                priority=2,
            )
        )

        return blocks

    def create_memory(
        self,
        session_id: str,
        token_limit: int | None = None,
        chat_history_token_ratio: float | None = None,
        token_flush_size: int | None = None,
        memory_blocks: list[BaseMemoryBlock] | None = None,
        insert_method: str | None = None,
    ) -> Memory:
        """Create a new memory for a specific session.
        Args"""
        token_limit = token_limit or self.DEFAULT_TOKEN_LIMIT
        chat_history_token_ratio = chat_history_token_ratio or self.DEFAULT_CHAT_HISTORY_TOKEN_RATIO
        token_flush_size = token_flush_size or self.DEFAULT_TOKEN_FLUSH_SIZE
        insert_method = insert_method or self.DEFAULT_INSERT_METHOD

        if memory_blocks is None:
            memory_blocks = self._create_default_memory_blocks()

        memory = Memory.from_defaults(
            session_id=session_id,
            token_limit=token_limit,
            chat_history_token_ratio=chat_history_token_ratio,
            token_flush_size=token_flush_size,
            memory_blocks=memory_blocks,
            insert_method=insert_method,
        )

        return memory


def get_memory_manager() -> MemoryManager:
    """Get the memory manager singleton instance."""
    if (
        not hasattr(get_memory_manager, "_instance")
        or get_memory_manager._instance is None
    ):
        get_memory_manager._instance = MemoryManager(llm=LlamaIndexSettings.llm)
    return get_memory_manager._instance
