from fastapi import Depends
from datetime import datetime
from app.core.tools.query_engine import QueryEngine, get_query_engine
from app.models.ask_ai.utils import Topic
from app.models.ask_ai.variable import ApiVariableParseOutput
from app.schemas.ask_ai.formalize_response import FormalizeResponseDto
from app.schemas.ask_ai.parse_api_variables import ParseApiVariablesDto
from app.schemas.ask_ai.ticket_analyze import TicketAnalyzeDto
from app.schemas.ask_ai.draft_response import DraftResponseDto, DraftResponseResultDto
from .correct_spelling import correct_spelling as cp
from .simplify_words import simplify_words as spw
from .shorten_response import shorten_response as sr
from .lengthen_response import lengthen_response as lr
from .ticket_analyze import ticket_analyze as ta
from .more_casual import more_casual as mc
from .more_professional import more_professional as mp
from .parse_api_variables import parse_api_variables as pav
from app.core.agents.workflows.assist_reply import AssistReplyWorkflow
from app.services.ask_ai.constants.common import WorkflowMode
from app.schemas.ask_ai.ticket import Ticket
from app.services.ask_ai.constants.ticket import TicketPriority, TicketStatus
from app.schemas.ask_ai.auto_response import AutoResponseDto, AutoResponseResultDto
from app.schemas.ask_ai.message_segment import MessageSegment
from app.core.logger import get_logger
from app.services.ask_ai.memory_integration import retrieve_and_inject_memory

logger = get_logger(__name__)

class AskAIService():
    def __init__(self):
        pass

    def _resolve_max_messages(self) -> int:
        try:
            from app.settings import settings
            return max(1, int(getattr(settings.llm, "max_history_messages", 10)))
        except (AttributeError, ValueError, TypeError):
            return 10

    def _truncate_history(self, messages: list, max_msgs: int) -> list:
        if not messages:
            return []
        return messages[-max_msgs:] if len(messages) > max_msgs else messages

    def _prepare_chat_history(self, raw_messages: list) -> list:
        from app.core.agents.workflows.assist_reply.helpers import build_chat_history
        return build_chat_history(raw_messages)

    def _apply_doc_filter(self, query_engine: QueryEngine, doc_ids: list[str] | None) -> None:
        if doc_ids:
            query_engine.set_doc_filter(doc_ids)

    def _build_contexts(self, data) -> tuple[dict | None, dict | None, dict | None, dict | None]:
        from app.core.agents.workflows.assist_reply.helpers import build_context_dicts
        return build_context_dicts(data)

    def _build_topics(self, topic_schemas: list, user_id: str | None) -> list[Topic]:
        from app.core.agents.workflows.assist_reply.helpers import build_topics
        return build_topics(topic_schemas, user_id)

    async def _run_assist_reply_workflow(
        self,
        *,
        agent_name: str = "",
        org_desc: str = "",
        chat_history: list = None,
        rules: list[str] | None = None,
        response_template: str | None = None,
        topics: list[Topic] | None = None,
        channel = None,
        tone: str | None = None,
        language: str | None = None,
        additional_context: dict[str, str] | None = None,
        query_engine: QueryEngine | None = None,
        current_ticket_status: str = "",
        customer_context: dict | None = None,
        email_metadata: dict | None = None,
        ticket_info: dict | None = None,
        conversation_context: dict | None = None,
        mode: WorkflowMode = WorkflowMode.AUTO_RESPONSE,
    ) -> dict:
        if chat_history is None:
            chat_history = []
        if rules is None:
            rules = []
        if topics is None:
            topics = []
        if additional_context is None:
            additional_context = {}

        agent = AssistReplyWorkflow(timeout=None)

        additional_context["template_version"] = "RichPromptTemplate_v1.0"
        additional_context["flow_start_time"] = datetime.now().isoformat()

        try:
            handler = agent.run(
                chat_history=chat_history,
                agent_name=agent_name,
                org_desc=org_desc,
                topics=topics,
                rules=rules,
                response_template=response_template,
                channel=channel,
                tone=tone,
                language=language,
                additional_context=additional_context,
                query_engine=query_engine,
                current_ticket_status=current_ticket_status,
                customer_context=customer_context,
                email_metadata=email_metadata,
                ticket_info=ticket_info,
                conversation_context=conversation_context,
                mode=mode,
            )
            result_dict = await handler
            return result_dict
        except Exception as e:
            logger.error("Auto response flow failed: %s", str(e), exc_info=True)
            error_type = type(e).__name__
            error_msg = str(e)[:80]
            fallback_ticket = Ticket(
                status=TicketStatus.OPEN,
                priority=TicketPriority.HIGH,
                body=f"Workflow error ({error_type}): {error_msg}"
            )
            return {
                "response": [],
                "ticket": fallback_ticket.dict(),
                "agent_can_reply": False,
                "skipResponse": True,
                "skip_reason": error_type,
            }

    async def draft_response(self, data: DraftResponseDto, query_engine: QueryEngine = Depends(get_query_engine)) -> DraftResponseResultDto:
        topics: list[Topic] = self._build_topics(data.topics, data.user_id)
        max_msgs = self._resolve_max_messages()
        truncated = self._truncate_history(data.chat_history, max_msgs)
        chat_history = self._prepare_chat_history(truncated)
        self._apply_doc_filter(query_engine, data.doc_ids)
        customer_context_dict, email_metadata_dict, ticket_info_dict, conversation_context_dict = self._build_contexts(data)

        chatroom_id = conversation_context_dict.get("chatroom_id") if conversation_context_dict else None
        ticket_id = conversation_context_dict.get("ticket_id") if conversation_context_dict else None

        current_query = ""
        if data.chat_history:
            last_msg = data.chat_history[-1]
            current_query = last_msg.get("content", "") if isinstance(last_msg, dict) else ""

        additional_context = data.additional_context.copy() if data.additional_context else {}
        logger.info("[DraftResponse] Additional context: %s", additional_context)
        if chatroom_id and ticket_id:
            logger.info("[DraftResponse] Retrieving memory for chatroom_id: %s, ticket_id: %s", chatroom_id, ticket_id)
            additional_context = await retrieve_and_inject_memory(
                chatroom_id=chatroom_id,
                ticket_id=ticket_id,
                current_query=current_query,
                additional_context=additional_context,
            )

        result_dict = await self._run_assist_reply_workflow(
            agent_name=data.agent_name,
            org_desc=data.org_desc,
            chat_history=chat_history,
            rules=data.rules,
            response_template=data.response_template,
            topics=topics,
            channel=data.channel,
            tone=data.tone,
            language=data.language,
            additional_context=additional_context,
            query_engine=query_engine,
            customer_context=customer_context_dict,
            email_metadata=email_metadata_dict,
            ticket_info=ticket_info_dict,
            conversation_context=conversation_context_dict,
            mode=WorkflowMode.DRAFT,
        )

        response_segments = []
        if result_dict.get("response"):
            response_segments = [
                MessageSegment(**msg) if isinstance(msg, dict) else msg
                for msg in result_dict["response"]
            ]

        return DraftResponseResultDto(
            response=response_segments
        )

    def draft_response_background(self, task_id: str, tenant_id: str, data: DraftResponseDto) -> dict:
        """
        Enqueue draft response generation as a background task.

        Args:
            task_id: Unique identifier for the task
            tenant_id: Tenant ID for the request
            data: Draft response request data

        Returns:
            Dict with task_id and status
        """
        from app.tasks.draft_response import draft_response_async
        from app.lib.constants.source_type import SourceStatusEnum

        _ = draft_response_async.delay(
            task_id=task_id,
            tenant_id=tenant_id,
            data=data.model_dump(),
        )

        return {
            "taskId": task_id,
            "status": SourceStatusEnum.INDEXING,  # Using same status as knowledge base tasks
        }

    async def auto_response(self, data: AutoResponseDto, query_engine: QueryEngine = Depends(get_query_engine)) -> AutoResponseResultDto:
        topics: list[Topic] = self._build_topics(data.topics, data.user_id)
        max_msgs = self._resolve_max_messages()
        truncated = self._truncate_history(data.chat_history, max_msgs)
        if len(data.chat_history or []) > max_msgs:
            logger.info(f"Applied max_msgs limit: keeping last {max_msgs} messages")
        chat_history = self._prepare_chat_history(truncated)
        self._apply_doc_filter(query_engine, data.doc_ids)
        customer_context_dict, email_metadata_dict, ticket_info_dict, conversation_context_dict = self._build_contexts(data)

        chatroom_id = conversation_context_dict.get("chatroom_id") if conversation_context_dict else None
        ticket_id = conversation_context_dict.get("ticket_id") if conversation_context_dict else None

        current_query = ""
        if data.chat_history:
            last_msg = data.chat_history[-1]
            current_query = last_msg.get("content", "") if isinstance(last_msg, dict) else ""

        additional_context = data.additional_context.copy() if data.additional_context else {}
        if chatroom_id and ticket_id:
            logger.info("[AutoResponse] Retrieving memory for chatroom_id: %s, ticket_id: %s", chatroom_id, ticket_id)
            additional_context = await retrieve_and_inject_memory(
                chatroom_id=chatroom_id,
                ticket_id=ticket_id,
                current_query=current_query,
                additional_context=additional_context
            )

        logger.info("[AutoResponse] Additional context: %s", additional_context)
        result_dict = await self._run_assist_reply_workflow(
            agent_name=data.agent_name,
            org_desc=data.org_desc,
            chat_history=chat_history,
            rules=data.rules,
            response_template=data.response_template,
            topics=topics,
            channel=data.channel,
            tone=data.tone,
            language=data.language,
            additional_context=additional_context,
            query_engine=query_engine,
            customer_context=customer_context_dict,
            email_metadata=email_metadata_dict,
            ticket_info=ticket_info_dict,
            conversation_context=conversation_context_dict,
            mode=WorkflowMode.AUTO_RESPONSE,
        )

        response_segments = []
        if result_dict.get("response"):
            response_segments = [
                MessageSegment(**msg) if isinstance(msg, dict) else msg
                for msg in result_dict["response"]
            ]

        return AutoResponseResultDto(
            response=response_segments,
            ticket=result_dict["ticket"],
            agent_can_reply=result_dict["agent_can_reply"],
            skipResponse=result_dict.get("skipResponse", False)
        )

    def correct_spelling(self, data: FormalizeResponseDto) -> str:
        return cp(text=data.text)

    def simplify_words(self, data: FormalizeResponseDto) -> str:
        return spw(text=data.text)

    def shorten_response(self, data: FormalizeResponseDto) -> str:
        return sr(text=data.text)

    async def lengthen_response(self, data: FormalizeResponseDto, query_engine: QueryEngine = Depends(get_query_engine)) -> str:
        if data.doc_ids:
            query_engine.set_doc_filter(data.doc_ids)
        else:
            query_engine = None

        return await lr(text=data.text, query_engine=query_engine)

    def more_casual(self, data: FormalizeResponseDto) -> str:
        return mc(text=data.text)

    def more_professional(self, data: FormalizeResponseDto) -> str:
        return mp(text=data.text)

    def ticket_analyze(self, data: TicketAnalyzeDto) -> str:
        return ta(conversation=data.conversation, language=data.language)

    def parse_api_variables(self, data: ParseApiVariablesDto) -> ApiVariableParseOutput:
        return pav(
            language=data.language,
            name=data.name,
            description=data.description,
            parameters=data.parameters,
            body=data.body,
            current_variables=data.current_variables,
        )

    async def generate_resolution_summary(self, data: dict) -> dict:
        from app.services.resolution_summary_service import resolution_summary_service
        try:
            ticket_info = data.get("ticket_info", {})

            chatroom_id = ticket_info.get("chatRoomID") if ticket_info else None
            ticket_id = ticket_info.get("ticketID") if ticket_info else None

            logger.info(f"Generating resolution summary for ticket {ticket_id} in chatroom {chatroom_id}")
            summary = await resolution_summary_service.generate_summary(
                ticket_info=ticket_info,
                messages=data.get("messages"),
                chatroom_id=chatroom_id,
                ticket_id=ticket_id
            )
            return {"summary": summary}
        except Exception as e:
            logger.error(f"Error generating resolution summary: {e}", exc_info=True)
            return {"summary": None, "error": str(e)}
