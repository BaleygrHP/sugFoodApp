from typing import Any
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core import Settings

from app.core.logger import get_logger
from app.core.prompts import TICKET_TRIAGE_ANALYSIS_TEMPLATE
from app.services.ask_ai.constants.ticket import TicketPriority, TicketStatus

from .domain import TriageContext, TriageDecision
from .registry import TriageStrategy


logger = get_logger(__name__)


class SkipFlagStrategy(TriageStrategy):
    name = "skip_flag"

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        if ctx.skip_triage:
            return TriageDecision(
                should_reactivate=True,
                should_skip=False,
                priority_level=TicketPriority.MEDIUM,
                confidence=0.5,
            )
        return None


class EmptyHistoryStrategy(TriageStrategy):
    name = "empty_history"

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        if not ctx.chat_history:
            return TriageDecision(
                should_reactivate=False,
                should_skip=True,
                skip_reason="Empty chat history",
                priority_level=TicketPriority.LOW,
                confidence=0.8,
                ticket_status=TicketStatus.UNASSIGNED,
            )
        return None


class OpenTicketStrategy(TriageStrategy):
    name = "open_ticket"

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        if (ctx.current_ticket_status or "").upper() == TicketStatus.OPEN.value:
            return TriageDecision(
                should_reactivate=False,
                should_skip=True,
                skip_reason="Human agent is currently handling",
                priority_level=TicketPriority.MEDIUM,
                confidence=0.9,
                ticket_status=TicketStatus.OPEN,
            )
        return None


class LLMDecisionStrategy(TriageStrategy):
    name = "llm_decision"

    def __init__(self, llm_timeout: float):
        self._timeout = llm_timeout

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        try:
            latest_user_message = None
            try:
                if ctx.chat_history:
                    last = ctx.chat_history[-1]
                    latest_user_message = getattr(last, 'content', None)
            except Exception:
                pass

            prompt_context = {
                "current_ticket_status": ctx.current_ticket_status,
                "latest_user_message": latest_user_message,
                "chat_history": ctx.chat_history,
                "channel": getattr(ctx.channel, 'value', None) or "unknown",
                "org_desc": ctx.org_desc,
                "additional_context": ctx.additional_context,
                "customer_context": ctx.customer_context,
                "email_metadata": ctx.email_metadata,
                "ticket_info": ctx.ticket_info,
                "conversation_context": ctx.conversation_context,
            }

            prompt_messages = TICKET_TRIAGE_ANALYSIS_TEMPLATE.format_messages(**prompt_context)
            logger.debug("Ticket triage - messages=%s status=%s", len(ctx.chat_history or []), ctx.current_ticket_status)

            from .domain import TriageDecision as _TD
            output_parser = PydanticOutputParser(_TD)

            import asyncio as _asyncio
            result = await _asyncio.wait_for(Settings.llm.achat(prompt_messages), timeout=self._timeout)

            logger.debug("Triage LLM responded")
            parsed = output_parser.parse(result.message.content)
            logger.info("Triage decision - should_skip: %s, should_reactivate: %s, priority: %s", parsed.should_skip, parsed.should_reactivate, parsed.priority_level)
            return parsed
        except (RuntimeError, AttributeError, TypeError, ValueError) as e:
            logger.error("Smart triage analysis failed: %s", str(e), exc_info=True)
            return None


class StatusFallbackStrategy(TriageStrategy):
    name = "status_fallback"

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        try:
            s = (ctx.current_ticket_status or "").upper()
            chat_history = ctx.chat_history or []
            if not s:
                return TriageDecision(should_reactivate=True, should_skip=False, skip_reason="", priority_level=TicketPriority.MEDIUM, confidence=0.7)
            if s in ["AI_SERVING"]:
                return TriageDecision(should_reactivate=True, should_skip=False, priority_level=TicketPriority.MEDIUM, confidence=0.7)
            if s in ["UNASSIGNED", "PENDING"]:
                return TriageDecision(should_reactivate=True, should_skip=False, priority_level=TicketPriority.MEDIUM, confidence=0.7)
            if s in ["SOLVED"]:
                should_reactivate = bool(chat_history and len(chat_history) > 0)
                return TriageDecision(should_reactivate=should_reactivate, should_skip=not should_reactivate, skip_reason=("Customer continued conversation after ticket was solved" if should_reactivate else "Ticket was solved"), priority_level=TicketPriority.MEDIUM, confidence=0.7)
            return TriageDecision(should_reactivate=False, should_skip=True, skip_reason=f"Unknown status {ctx.current_ticket_status} - conservative approach", priority_level=TicketPriority.MEDIUM, confidence=0.7)
        except Exception:
            return None
