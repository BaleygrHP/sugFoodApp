from typing import Optional
from app.core.agents.agent_manager import AgentManager
from app.core.logger import get_logger
from app.core.memory import get_memory_manager
from app.core.prompts.base.resolution_summary import RESOLUTION_SUMMARY_PROMPT

logger = get_logger(__name__)

MEMORY_BATCH_SIZE = 50  # Used by mem0 manager's add_messages_batched()


class ResolutionSummaryService:
    def __init__(self):
        self.agent_manager = AgentManager()
        self._memory_manager = None  # Lazy initialization

    def _get_memory_manager(self):
        """Get or create a single shared memory manager instance."""
        if self._memory_manager is None:
            self._memory_manager = get_memory_manager()
        return self._memory_manager


    async def generate_summary(
        self,
        ticket_info: dict = None,
        messages: list = None,
        chatroom_id: str = None,
        ticket_id: str = None
    ) -> Optional[str]:
        try:
            context_parts = []
            if ticket_info:
                context_parts.append(f"Ticket: {ticket_info.get('title', 'N/A')}")
            if messages:
                msgs = []
                for m in messages:
                    role = m.get('role', 'user').upper()
                    content = m.get('content', '')
                    speaker = 'CS' if role in ['ASSISTANT', 'AGENT'] else 'KH'
                    msgs.append(f"{speaker}: {content[:200]}")
                context_parts.append("Conversation:\n" + "\n".join(msgs))

            llm = self.agent_manager.get_llm(system_prompt=RESOLUTION_SUMMARY_PROMPT)
            prompt = f"Summarize this support interaction concisely:\n\n{chr(10).join(context_parts)}\n\nSummary:"
            response = await llm.acomplete(prompt)
            summary = str(response).strip()

            if chatroom_id and ticket_id and messages:
                try:
                    await self._extract_customer_memory(
                        chatroom_id=chatroom_id,
                        ticket_id=ticket_id,
                        messages=messages
                    )
                except Exception as mem_err:
                    logger.error(f"Memory extraction failed (non-fatal): {mem_err}", exc_info=True)

            return summary
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    async def _extract_customer_memory(
        self,
        chatroom_id: str,
        ticket_id: str,
        messages: list
    ):
        """Extract customer memory using batched approach from mem0 manager"""
        try:
            if not messages or len(messages) < 2:
                return

            memory_mgr = self._get_memory_manager()

            # Use batched method from mem0 manager (handles batching internally)
            await memory_mgr.add_messages_batched(
                chatroom_id=chatroom_id,
                ticket_id=ticket_id,
                messages=messages,
                batch_size=MEMORY_BATCH_SIZE
            )

        except Exception as e:
            logger.error(f"[MEMORY] Failed to extract customer memory for ticket {ticket_id}: {e}")


resolution_summary_service = ResolutionSummaryService()
__all__ = ["ResolutionSummaryService", "resolution_summary_service"]
