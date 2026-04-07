"""Auto response workflow for AI agents."""
from typing import Any
from datetime import datetime

from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context,
)
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage
from llama_index.core.output_parsers import PydanticOutputParser

from app.models.ask_ai.utils import Topic
from app.schemas.ask_ai.auto_response import MessageSegment
from app.schemas.ask_ai.ticket import Ticket
from app.services.ask_ai.constants.ticket import TicketStatus, TicketPriority
from app.services.ask_ai.constants.common import Channel, WorkflowMode
from app.core.tools.query_engine import QueryEngine
from app.core.logger import get_logger
from app.core.prompts import (
    AUTO_RESPONSE_COMPLETE_TEMPLATE,
)

from .models import UnifiedResponseWithSegmentation
from .events import TicketTriageEvent, AnswerQuestionEvent
from app.core.agents.workflows.utils.agent_builder import (
    normalize_language,
    build_query_engine_tools,
    build_init_agent,
    build_topic_agents,
)
from .helpers import (
    get_latest_user_message,
    run_init_agent,
    run_topic_agents_parallel,
    run_knowledge_query,
    normalize_segments,
    validate_segments,
    extract_image_urls,
    create_stop_event_result,
    KNOWLEDGE_TOP_K,
    LLM_TIMEOUT,
)
from .triage.domain import TriageContext, default_activate_decision
from .triage.registry import build_default_triage_registry
from .triage.strategies import (
    SkipFlagStrategy,
    EmptyHistoryStrategy,
    OpenTicketStrategy,
    LLMDecisionStrategy,
    StatusFallbackStrategy,
)


logger = get_logger(__name__)




class AssistReplyWorkflow(Workflow):
    def __init__(
        self,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)



    @step
    async def setup(
        self, ctx: Context, ev: StartEvent
    ) -> TicketTriageEvent | AnswerQuestionEvent:
        """Set up the workflow with initial parameters."""
        chat_history = ev.get("chat_history")
        topics: list[Topic] = ev.get("topics", default=[])
        rules = ev.get("rules", default=[])
        agent_name: str = ev.get("agent_name", default="")
        org_desc: str = ev.get("org_desc", default="")
        channel = ev.get("channel", default=Channel.CHAT)
        tone = ev.get("tone")
        language = ev.get("language", default="")
        response_template = ev.get("response_template", default="")
        query_engine: QueryEngine = ev.get("query_engine")
        additional_context: dict[str, str] = ev.get("additional_context", default={})
        mode = ev.get("mode", default=WorkflowMode.AUTO_RESPONSE)
        skip_triage = ev.get("skip_triage", default=False)

        customer_context = ev.get("customer_context", default=None)
        email_metadata = ev.get("email_metadata", default=None)
        ticket_info = ev.get("ticket_info", default=None)
        conversation_context = ev.get("conversation_context", default=None)

        current_ticket_status = ""
        ticket_source = ""
        if ticket_info:
            current_ticket_status = ticket_info.get("status", "")
            ticket_source = ticket_info.get("source", "")

        if chat_history is None:
            chat_history = [ChatMessage(role="user", content=".")]

        if not channel:
            channel = Channel.CHAT
        language = normalize_language(language)

        if not tone:
            tone = "Friendly and professional"
        if not language:
            language_text = "Analyze the user's messages and detect their language. Respond exclusively in that language."
        else:
            language_text = f"Respond in {language}"


        setup_ctx = {
            "chat_history": chat_history,
            "topics": topics,
            "rules": rules,
            "agent_name": agent_name,
            "org_desc": org_desc,
            "channel": channel,
            "tone": tone,
            "language": language,
            "language_text": language_text,
            "response_template": response_template,
            "additional_context": additional_context,
            "query_engine": query_engine,
            "current_ticket_status": current_ticket_status,
            "ticket_source": ticket_source,
            "customer_context": customer_context,
            "email_metadata": email_metadata,
            "ticket_info": ticket_info,
            "conversation_context": conversation_context,
            "mode": mode,
            "skip_triage": skip_triage,
        }

        for k, v in setup_ctx.items():
            await ctx.set(k, v)

        # Skip triage for DRAFT mode and go directly to response generation
        if mode == WorkflowMode.DRAFT:
            triage_info = TicketTriageEvent(
                should_reactivate=False,
                should_skip=False,
                skip_reason="",
                priority_level=TicketPriority.MEDIUM,
                confidence=1.0,
                current_ticket_status=current_ticket_status
            )
            await ctx.set("triage_info", triage_info)
            return AnswerQuestionEvent(triage_info=triage_info)

        return TicketTriageEvent(
            should_reactivate=False,
            should_skip=False,
            skip_reason="",
            priority_level=TicketPriority.MEDIUM,
            confidence=0.0,
            current_ticket_status=current_ticket_status
        )

    @step
    async def ticket_triage(
        self, ctx: Context, ev: TicketTriageEvent
    ) -> AnswerQuestionEvent | StopEvent:
        """Analyze ticket and determine if AI should respond."""
        try:
            mode = await ctx.get("mode", WorkflowMode.AUTO_RESPONSE)
            current_ticket_status = ev.current_ticket_status or await ctx.get("current_ticket_status", "")
            triage_ctx = TriageContext(
                current_ticket_status=current_ticket_status,
                chat_history=await ctx.get("chat_history"),
                channel=await ctx.get("channel"),
                org_desc=await ctx.get("org_desc", ""),
                additional_context=await ctx.get("additional_context", {}),
                customer_context=await ctx.get("customer_context", None),
                email_metadata=await ctx.get("email_metadata", None),
                ticket_info=await ctx.get("ticket_info", None),
                conversation_context=await ctx.get("conversation_context", None),
                skip_triage=await ctx.get("skip_triage", False),
            )

            strategies = [
                SkipFlagStrategy(),
                EmptyHistoryStrategy(),
                LLMDecisionStrategy(LLM_TIMEOUT),
                StatusFallbackStrategy(),
            ]
            if mode != WorkflowMode.DRAFT:
                strategies.insert(2, OpenTicketStrategy())

            registry = build_default_triage_registry(strategies)

            decision = None
            for strat in registry:
                d = await strat.decide(triage_ctx)
                if d is not None:
                    decision = d
                    break

            if decision is None:
                decision = default_activate_decision()

            if decision.should_skip:
                status = decision.ticket_status or (
                    TicketStatus[current_ticket_status.upper()] if current_ticket_status and current_ticket_status.upper() in TicketStatus.__members__ else TicketStatus.UNASSIGNED
                )
                ticket = Ticket(
                    status=status,
                    priority=decision.priority_level,
                    body=decision.skip_reason
                )
                return StopEvent(result={
                    "response": [],
                    "ticket": ticket.dict(),
                    "agent_can_reply": False,
                    "skipResponse": True,
                    "skip_reason": decision.skip_reason
                })

            triage_info = TicketTriageEvent(
                should_reactivate=decision.should_reactivate,
                should_skip=decision.should_skip,
                skip_reason=decision.skip_reason,
                priority_level=decision.priority_level,
                confidence=decision.confidence,
                current_ticket_status=current_ticket_status
            )
            await ctx.set("triage_info", triage_info)
            return AnswerQuestionEvent(triage_info=triage_info)

        except (RuntimeError, AttributeError, TypeError, ValueError) as e:
            logger.error("Smart triage analysis failed: %s", str(e), exc_info=True)
            return None

    @step
    async def generate_auto_response(
        self, ctx: Context, _ev: AnswerQuestionEvent
    ) -> StopEvent:
        """Generate automated response using AI agents."""

        topics = await ctx.get("topics")
        rules = await ctx.get("rules")
        agent_name = await ctx.get("agent_name")
        org_desc = await ctx.get("org_desc")
        channel = await ctx.get("channel")
        tone = await ctx.get("tone")
        language_text = await ctx.get("language_text")
        response_template = await ctx.get("response_template")
        additional_context = await ctx.get("additional_context")
        chat_history = await ctx.get("chat_history")
        customer_context = await ctx.get("customer_context", None)
        conversation_context = await ctx.get("conversation_context", None)
        ticket_source = await ctx.get("ticket_source", "")
        current_ticket_status = await ctx.get("current_ticket_status", "")
        query_engine = await ctx.get("query_engine", None)

        outputs = []
        try:
            import asyncio
            from app.core.agents.workflows.utils.parallel_executor import execute_agents_parallel
            from .helpers import build_knowledge_context as _build_knowledge_context

            query_engine_tools, query_engine_available = build_query_engine_tools(query_engine)

            kb_context_text = ""

            init_agent = build_init_agent(
                agent_name=agent_name,
                org_desc=org_desc,
                tone=tone,
                language_text=language_text,
                rules=rules or [],
                response_template=response_template or "",
                additional_context=additional_context or {},
                query_engine_available=query_engine_available,
                use_customer_coordinator=False,
                tools=query_engine_tools,
            )

            topic_agents = build_topic_agents(
                topics=topics or [],
                agent_name=agent_name,
                org_desc=org_desc,
                tone=tone,
                language_text=language_text,
                rules=rules or [],
                response_template=response_template or "",
                additional_context=additional_context or {},
                query_engine_tools=query_engine_tools,
                mode=WorkflowMode.AUTO_RESPONSE,
                kb_context=kb_context_text,
            )

            try:
                topic_agent_names = [getattr(a, "name", "?") for a in (topic_agents or [])]
                logger.info(
                    "[AutoResponse] Built %s topic agents: %s | init_agent=%s",
                    len(topic_agent_names),
                    topic_agent_names,
                    getattr(init_agent, "name", "init"),
                )
            except Exception:
                pass

            task_names = []
            tasks_by_key = {}

            # Add init agent as parallel task (non-blocking)
            if init_agent:
                task_names.append("init_agent")
                tasks_by_key["init_agent"] = run_init_agent(init_agent, chat_history)
                logger.debug("[AutoResponse] Init agent queued for parallel execution")

            if topic_agents:
                task_names.append(f"topic_agents({len(topic_agents)})")
                try:
                    names = [getattr(a, "name", "?") for a in topic_agents]
                    logger.debug("[AutoResponse] Executing topic agents: %s", names)
                except Exception:
                    pass
                tasks_by_key["topic_agents"] = run_topic_agents_parallel(
                    execute_agents_parallel, topic_agents, chat_history
                )

            # Query knowledge base in parallel with topic agents once
            if query_engine:
                safe_context = _build_knowledge_context(chat_history, conversation_context, max_messages=5)
                if safe_context:
                    task_names.append("knowledge_query")
                    tasks_by_key["knowledge_query"] = run_knowledge_query(
                        query_engine, safe_context, top_k=KNOWLEDGE_TOP_K
                    )

            if tasks_by_key:
                logger.debug("Running %s tasks in parallel: %s", len(tasks_by_key), ', '.join(task_names))
                start_time = datetime.now()
                results_list = await asyncio.gather(*tasks_by_key.values(), return_exceptions=True)
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.debug("Parallel execution completed in %.2fs", elapsed)

                key_order = list(tasks_by_key.keys())
                results = {k: results_list[i] for i, k in enumerate(key_order)}

                # Process init agent result (if it ran in parallel)
                if "init_agent" in results:
                    init_content = results["init_agent"]
                    if isinstance(init_content, Exception):
                        logger.warning("Init agent failed (non-critical): %s", init_content)
                    elif isinstance(init_content, str) and init_content.strip():
                        outputs.append(init_content)
                        logger.debug("Init agent completed in parallel: %s chars", len(init_content))
                    else:
                        logger.debug("Init agent returned empty content")

                if "topic_agents" in results:
                    topic_outputs = results["topic_agents"]
                    if isinstance(topic_outputs, Exception):
                        logger.error("Topic agents failed: %s", topic_outputs)
                    else:
                        outputs.extend(topic_outputs)
                        logger.info(
                            "[AutoResponse] Topic agents outputs: %s items, total %s chars | First 200 chars: %s",
                            len(topic_outputs),
                            sum(len(o) for o in topic_outputs if isinstance(o, str)),
                            topic_outputs[0][:200] if topic_outputs and isinstance(topic_outputs[0], str) else "N/A"
                        )

                if "knowledge_query" in results and isinstance(results["knowledge_query"], dict):
                    try:
                        sources = results["knowledge_query"].get('sources', [])
                        if sources:
                            kb_docs = []
                            for idx, source in enumerate(sources[:5], 1):
                                text = source.get('text', '')
                                if text and text.strip():
                                    kb_docs.append(f"Document {idx}:\n{text}\n")
                            if kb_docs:
                                kb_context_text = "\n".join(kb_docs)
                                outputs.append(kb_context_text)
                                logger.info("[AutoResponse] KB context prepared: %s documents", len(sources))
                    except Exception:
                        pass

        except (RuntimeError, AttributeError, TypeError, ValueError) as e:
            logger.error("Parallel workflow failed: %s", e, exc_info=True)

        latest_msg_for_response = get_latest_user_message(chat_history)
        logger.debug("[Response] latest_user_message available; history_len=%s", len(chat_history))

        # Log outputs for debugging
        logger.info(
            "[AutoResponse] Unified context outputs: %s items, total %s chars",
            len(outputs),
            sum(len(o) for o in outputs if isinstance(o, str))
        )
        if outputs:
            for idx, out in enumerate(outputs[:3]):  # Log first 3 outputs
                logger.info(
                    "[AutoResponse] Output[%s] preview: %s... (%s chars)",
                    idx,
                    str(out)[:150] if isinstance(out, str) else type(out).__name__,
                    len(out) if isinstance(out, str) else 0
                )

        unified_context = {
            "outputs": outputs,
            "chat_history": chat_history,
            "latest_user_message": latest_msg_for_response,
            "topics": topics or [],
            "rules": rules or [],
            "agent_name": agent_name,
            "org_desc": org_desc,
            "channel": channel.value if channel else "CHAT",
            "tone": tone,
            "language": language_text,
            "response_template": response_template,
            "additional_context": additional_context,
            "facts_context": (additional_context.get("facts_context") if isinstance(additional_context, dict) else None),
            "customer_context": customer_context,
            "conversation_context": conversation_context,
            "ticket_source": ticket_source,
            "current_ticket_status": current_ticket_status,
        }

        try:
            prompt_messages = AUTO_RESPONSE_COMPLETE_TEMPLATE.format_messages(**unified_context)

            try:
                if chat_history:
                    last_msg = chat_history[-1]
                    add_kwargs = getattr(last_msg, 'additional_kwargs', {}) or {}
                    imgs = add_kwargs.get('images') or []
                    if imgs:
                        image_items = []
                        for img in imgs[:self.MAX_IMAGE_ATTACH]:
                            try:
                                url = (img.get('image_url') or {}).get('url', '')
                                if url:
                                    image_items.append({"type": "image_url", "image_url": {"url": url}})
                            except (TypeError, ValueError, KeyError):
                                continue
                        if image_items:
                            from llama_index.core.base.llms.types import ChatMessage as _CM, MessageRole as _MR
                            prompt_messages.append(
                                _CM(role=_MR.USER, content="Please analyze the attached image(s) to answer accurately.", additional_kwargs={"images": image_items})
                            )
                            logger.info("[AutoResponse] Attached %s image(s) to prompt.", len(image_items))
            except (AttributeError, TypeError, ValueError, KeyError):
                pass
            logger.debug("Auto response - messages=%s rules=%s", len(chat_history), len(rules or []))

            output_parser = PydanticOutputParser(UnifiedResponseWithSegmentation)
            import asyncio as _asyncio
            result = await _asyncio.wait_for(Settings.llm.achat(prompt_messages), timeout=LLM_TIMEOUT)

            logger.debug("Unified response LLM responded")

            import re as _re
            raw_content = result.message.content or ""
            fenced_match = _re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_content)
            if fenced_match:
                raw_content = fenced_match.group(1)

            parsed_result = output_parser.parse(raw_content)

            if parsed_result.reasoning:
                logger.info("LLM Reasoning: %s", parsed_result.reasoning)

            logger.info(
                "Unified response - should_skip: %s, segments: %s, ticket_status: %s",
                parsed_result.should_skip, len(parsed_result.segments), parsed_result.ticket_status
            )

            if parsed_result.should_skip:
                ticket = Ticket(
                    status=TicketStatus.AI_SERVING,
                    priority=parsed_result.ticket_priority,
                    body=parsed_result.ticket_summary or parsed_result.skip_reason
                )

                return StopEvent(result={
                    "response": [],
                    "ticket": ticket.dict(),
                    "agent_can_reply": False,
                    "skipResponse": True,
                    "skip_reason": parsed_result.skip_reason
                })

            cleaned_segments: list[MessageSegment] = normalize_segments(parsed_result.segments, extract_image_urls)

            messages = validate_segments(cleaned_segments)

            ticket = Ticket(
                status=parsed_result.ticket_status,
                priority=parsed_result.ticket_priority,
                body=parsed_result.ticket_summary
            )

            return create_stop_event_result(
                messages=messages,
                ticket=ticket,
                agent_can_reply=parsed_result.agent_can_reply,
                skip_response=False
            )

        except (RuntimeError, AttributeError, TypeError, ValueError) as e:
            logger.error("Unified response generation failed: %s", str(e), exc_info=True)

            error_type = type(e).__name__
            error_msg = str(e)[:100]

            ticket = Ticket(
                status=TicketStatus.OPEN,
                priority=TicketPriority.HIGH,
                body=f"AI error ({error_type}): {error_msg}"
            )

            return StopEvent(result={
                "response": [],
                "ticket": ticket.dict(),
                "agent_can_reply": False,
                "skipResponse": True,
                "skip_reason": f"System error: {error_type}"
            })
