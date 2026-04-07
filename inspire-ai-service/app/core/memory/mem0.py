import os
import time
import asyncio
from typing import Optional
from llama_index.core.llms import LLM
from app.core.logger import get_logger
from app.settings import settings
from app.core.prompts.helpdesk_memory_prompts import (
    HELPDESK_FACT_EXTRACTION_PROMPT,
    HELPDESK_UPDATE_MEMORY_PROMPT
)

logger = get_logger(__name__)


class Mem0Manager:
    MAX_MEMORIES = 50

    def __init__(self, llm: LLM):
        self.llm = llm
        self.memory = None

    def _get_mem0_config(self) -> dict:
        if settings.llm.gemini.api_key:
            os.environ["GOOGLE_API_KEY"] = settings.llm.gemini.api_key

        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "jarvis_helpdesk_memory",
                    "url": settings.infra.vector_store.url,
                    "api_key": settings.infra.vector_store.api_key,
                    "embedding_model_dims": 768,
                }
            },
            "llm": {
                "provider": "litellm",
                "config": {
                    "model": "gemini/gemini-2.0-flash-exp",
                    "temperature": 0.3,
                    "max_tokens": 4096,
                }
            },
            "embedder": {
                "provider": "gemini",
                "config": {
                    "model": "models/text-embedding-004",
                    "embedding_dims": 768
                }
            },
            "version": "v1.1",
            "custom_fact_extraction_prompt": HELPDESK_FACT_EXTRACTION_PROMPT,
            "custom_update_memory_prompt": HELPDESK_UPDATE_MEMORY_PROMPT
        }

        return config

    def _get_memory(self):
        if self.memory is None:
            try:
                from mem0 import Memory

                config = self._get_mem0_config()
                self.memory = Memory.from_config(config)
            except ImportError:
                logger.error("mem0ai not installed. Run: pip install mem0ai")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Mem0: {str(e)}")
                raise

        return self.memory

    async def add_messages(
        self,
        chatroom_id: str,
        ticket_id: str,
        messages: list[dict]
    ) -> dict:
        try:
            memory = self._get_memory()

            metadata = {
                "chatroom_id": chatroom_id,
                "ticket_id": ticket_id,
                "timestamp": time.time()
            }

            result = memory.add(
                    messages=messages,
                    user_id=chatroom_id,
                    metadata=metadata
                )

            facts = result.get("results", [])

            if facts:
                return [fact.get("memory") for fact in facts if fact.get("memory")] or []
            return []
        except Exception as e:
            logger.error(f"Error adding messages: {str(e)}")
            return []

    async def add_messages_batched(
        self,
        chatroom_id: str,
        ticket_id: str,
        messages: list[dict],
        batch_size: int = 20
    ) -> dict:
        if len(messages) <= batch_size:
            return await self.add_messages(chatroom_id, ticket_id, messages)

        all_results = []

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]

            try:
                result = await self.add_messages(
                    chatroom_id=chatroom_id,
                    ticket_id=ticket_id,
                    messages=batch
                )

                all_results.append(result)

            except Exception as e:
                logger.info("Error adding batch: %s", e)
                raise e from e

        return all_results

    async def retrieve_context(
        self,
        chatroom_id: str,
        ticket_id: str,
        query: str,
    ) -> list[dict]:
        try:
            memory = self._get_memory()

            results = memory.search(
                query=query,
                user_id=chatroom_id,
                filters={
                    "chatroom_id": chatroom_id,
                    "ticket_id": ticket_id,
                },
                limit=self.MAX_MEMORIES
            )

            logger.info("[MEMORY] Results: %s", results)

            results = [fact.get("memory") for fact in results.get("results", []) if fact.get("memory")]
            return results
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []

    def get_all_memories(
        self,
        chatroom_id: str,
        ticket_id: Optional[str] = None
    ) -> list[dict]:
        try:
            memory = self._get_memory()

            filters = {"chatroom_id": chatroom_id}
            if ticket_id:
                filters["ticket_id"] = ticket_id

            results = memory.get_all(
                user_id=chatroom_id,
                filters=filters
            )

            return results.get("results", [])

        except Exception as e:
            logger.error(f"Error getting all memories: {str(e)}")
            return []

    def delete_ticket_memories(self, chatroom_id: str, ticket_id: str) -> bool:
        try:
            memory = self._get_memory()

            memories = self.get_all_memories(chatroom_id, ticket_id)

            for mem in memories:
                memory_id = mem.get("id")
                if memory_id:
                    memory.delete(memory_id=memory_id)

            logger.info(f"Deleted {len(memories)} memories for ticket {ticket_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting ticket memories: {str(e)}")
            return False


def get_memory_manager(llm: LLM = None) -> Mem0Manager:
    if llm is None:
        from llama_index.core import Settings as LlamaIndexSettings
        llm = LlamaIndexSettings.llm

    if not hasattr(get_memory_manager, "_instance"):
        get_memory_manager._instance = Mem0Manager(llm)
        logger.info("Created new Mem0Manager instance")

    return get_memory_manager._instance
