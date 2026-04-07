from typing import Any, Tuple, List

from llama_index.core import Settings
from llama_index.core.agent.workflow import FunctionAgent

from app.core.tools.query_engine import QueryEngine
from app.core.prompts.domain.lazada import DefaultTopic, get_prompt_template_by_topic
from app.core.prompts import (
    CUSTOMER_COORDINATOR_TEMPLATE,
    SPECIALIST_AGENT_TEMPLATE,
    INIT_AGENT_PROMPT_TEMPLATE,
    TOPIC_AGENT_PROMPT_TEMPLATE,
)
from app.services.ask_ai.constants.common import WorkflowMode
from app.models.ask_ai.utils import Topic


def normalize_language(language: str | None) -> str:
    if not language:
        return (
            "Always respond in the same language used by the customer. "
            "Avoid using a different language that might confuse or frustrate them."
        )
    return f"Respond in {language}."


def build_query_engine_tools(query_engine: QueryEngine | None) -> Tuple[List[Any], bool]:
    if not query_engine:
        return [], False
    tools = [
        query_engine.create_tool(
            name="DefaultToolFnSchema",
            description=(
                "Use this tool to answer user questions using internal company documentation, "
                "especially for topics like payment methods, booking terms, or service policies."
                "Only use this if no specialized tools are available for the question."
            ),
        )
    ]
    return tools, True


def build_init_agent(
    agent_name: str,
    org_desc: str,
    tone: str | None,
    language_text: str,
    rules: list[str],
    response_template: str,
    additional_context: dict[str, str],
    query_engine_available: bool,
    use_customer_coordinator: bool,
    tools: List[Any] | None = None,
) -> FunctionAgent:
    from app.core.prompts.utils.formatter import format_prompt_with_fallback

    facts_context = additional_context.get("facts_context", []) if isinstance(additional_context, dict) else []

    template = (
        CUSTOMER_COORDINATOR_TEMPLATE if use_customer_coordinator else INIT_AGENT_PROMPT_TEMPLATE
    )
    context = {
        "agent_name": agent_name,
        "org_desc": org_desc,
        "tone": tone,
        "language": language_text,
        "rules": rules,
        "response_template": response_template,
        "additional_context": additional_context,
        "facts_context": facts_context,
        "query_engine_available": query_engine_available,
    }
    prompt = format_prompt_with_fallback(template, context, fallback_template="")
    if not prompt:
        prompt = (
            f"You are {agent_name}, a customer support coordinator."
            if use_customer_coordinator
            else f"You are {agent_name}, a support agent."
        )

    from app.core.logger import get_logger
    logger = get_logger(__name__)
    tool_count = len(tools or [])

    return FunctionAgent(
        name="Init Agent",
        description=(
            "Initial agent that analyzes user input and hands off to specialized agents or "
            "finishes if nothing to answer"
        ),
        system_prompt=prompt,
        llm=Settings.agentic_llm,
        tools=tools or [],
        max_function_calls=5,  # Init agent should complete quickly
    )


def build_topic_agents(
    topics: list[Topic],
    agent_name: str,
    org_desc: str,
    tone: str | None,
    language_text: str,
    rules: list[str],
    response_template: str,
    additional_context: dict[str, str],
    query_engine_tools: list[Any],
    mode: WorkflowMode,
    kb_context: str = "",
) -> list[FunctionAgent]:
    from app.core.prompts.utils.formatter import format_prompt_with_fallback

    facts_context = additional_context.get("facts_context", []) if isinstance(additional_context, dict) else []

    default_topic_codes = [topic.value for topic in DefaultTopic]
    agents: list[FunctionAgent] = []

    for topic in topics:
        topic_system_prompt = ""
        if (
            getattr(topic, "default_topic_code", None) is not None
            and topic.default_topic_code.startswith("lazada")
            and topic.default_topic_code in default_topic_codes
        ):
            template = get_prompt_template_by_topic(topic.default_topic_code, mode)
            if template:
                topic_system_prompt = format_prompt_with_fallback(
                    template,
                    {
                        "agent_name": agent_name,
                        "org_desc": org_desc,
                        "tone": tone,
                        "language": language_text,
                        "rules": rules,
                        "response_template": response_template,
                        "additional_context": additional_context,
                        "facts_context": facts_context,
                    },
                )

        if not topic_system_prompt:
            template = (
                TOPIC_AGENT_PROMPT_TEMPLATE
                if mode == WorkflowMode.DRAFT
                else SPECIALIST_AGENT_TEMPLATE
            )
            topic_system_prompt = format_prompt_with_fallback(
                template,
                {
                    "agent_name": agent_name,
                    "org_desc": org_desc,
                    "tone": tone,
                    "language": language_text,
                    "instructions": getattr(topic, "instructions", []),
                    "rules": rules,
                    "response_template": response_template,
                    "additional_context": additional_context,
                    "facts_context": facts_context,
                    "query_engine_available": bool(query_engine_tools),
                },
            )

        final_system_prompt = topic_system_prompt or f"You are {agent_name}, a customer support agent specializing in {topic.topic_name}."

        if kb_context:
            from app.core.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"[AgentBuilder] Injecting KB context into topic agent '{topic.topic_name}' ({len(kb_context)} chars)")
            kb_section = f"\n\n<knowledge-base-context>\nThe following documents were retrieved from the knowledge base for this conversation. Use this information FIRST before calling any tools:\n\n{kb_context}\n\nIMPORTANT: Extract information from the knowledge base context above whenever possible. Only call tools if the knowledge base doesn't contain the required information.\n</knowledge-base-context>"
            final_system_prompt += kb_section

        # Detect if agent has tools and select appropriate LLM
        agent_tools = topic.get_tools() + query_engine_tools
        has_tools = len(agent_tools) > 0

        # Use tool_llm (temp=0.0) for deterministic tool execution when tools are present
        # Use agentic_llm (temp=0.7) for creative responses when no tools
        selected_llm = Settings.tool_llm if has_tools else Settings.agentic_llm

        from app.core.logger import get_logger
        logger = get_logger(__name__)

        # Verify temperature setting
        actual_temp = getattr(selected_llm, 'temperature', 'unknown')
        llm_type = f"tool_llm (configured_temp={actual_temp})" if has_tools else f"agentic_llm (configured_temp={actual_temp})"

        if has_tools and actual_temp != 0.0:
            logger.warning(
                f"[AgentBuilder] WARNING: Tool agent '{topic.topic_name}' temperature is {actual_temp}, expected 0.0 for deterministic execution!"
            )

        # Add max_function_calls to prevent infinite loops
        # Load from config (default: 10 iterations max)
        from app.core.agents.workflows.assist_reply.config import get_config
        config = get_config()

        agent = FunctionAgent(
            name=topic.topic_name,
            description=topic.description,
            system_prompt=final_system_prompt,
            llm=selected_llm,
            tools=agent_tools,
            max_function_calls=config.max_agent_iterations,  # Prevent infinite tool call loops
        )
        agents.append(agent)

    return agents
