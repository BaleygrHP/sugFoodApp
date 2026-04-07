from fastapi import Depends
from llama_index.core.agent import ReActAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool, FunctionTool

from app.core.tools.query_engine import QueryEngine
from app.core.logger import get_logger
from app.settings import settings
from app.settings.llm import Provider

logger = get_logger(__name__)


class AgentManager:
    """Basic manager for AI agents with support for custom tools and using ReAct agent"""

    def __init__(self, query_engine: QueryEngine = Depends()):
        self.tools: dict[str, BaseTool] = {}
        self.query_engine = query_engine
        self.llm_settings = settings.llm

        # Default agent settings
        self.verbose = True
        self.max_iterations = 10
        self.default_system_prompt = (
            "You are an AI assistant helping users with their questions. "
            "Use the tools available to provide accurate information."
        )

    def get_llm(self, system_prompt: str = None, temperature: float = None, max_tokens: int = None) -> LLM:
        """
        Get LLM with specific parameters

        Args:
            temperature: Controls randomness (0.0 to 1.0); uses default if None
            max_tokens: Maximum token limit for responses; uses default if None

        Returns:
            Configured LLM instance
        """
        # If no specific parameters are requested, use the global LLM
        if temperature is None and max_tokens is None and system_prompt is None:
            from llama_index.core import Settings as LlamaIndexSettings
            if LlamaIndexSettings.llm is not None:
                return LlamaIndexSettings.llm

        provider = settings.llm.provider.lower()
        temperature = (
            temperature
            if temperature is not None
            else (
                self.llm_settings.gemini.temperature
                if provider == Provider.GEMINI
                else self.llm_settings.openai.temperature
            )
        )
        max_tokens = (
            max_tokens
            if max_tokens is not None
            else (
                self.llm_settings.gemini.max_tokens
                if provider == Provider.GEMINI
                else self.llm_settings.openai.max_tokens
            )
        )
        system_prompt = (
            system_prompt if system_prompt is not None else self.default_system_prompt
        )

        if provider == Provider.GEMINI:
            # Create Gemini LLM
            from llama_index.llms.gemini import Gemini

            return Gemini(
                model=f"models/{self.llm_settings.gemini.model_name or 'gemini-2.0-flash-lite'}",
                api_key=self.llm_settings.gemini.api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
        elif provider == Provider.OPENAI:
            # Create OpenAI LLM
            from llama_index.llms.openai import OpenAI

            return OpenAI(
                model=self.llm_settings.openai.model_name or "gpt-3.5-turbo",
                api_key=self.llm_settings.openai.api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
        else:
            # Default to Gemini if provider is invalid
            logger.warning(f"Unknown provider '{provider}', defaulting to Gemini")
            from llama_index.llms.gemini import Gemini

            return Gemini(
                model=f"models/{self.llm_settings.gemini.model_name or 'gemini-2.0-flash-lite'}",
                api_key=self.llm_settings.gemini.api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )

    def register_tool(self, name: str, func: callable, description: str, parameters: dict = None) -> None:
        """
        Register a new tool for agents to use

        Args:
            name: Tool name
            func: Function that implements the tool
            description: Tool description
            parameters: Optional parameter schema for the tool
        """
        try:
            tool = FunctionTool.from_defaults(
                name=name,
                fn=func,
                description=description,
                parameters=parameters
            )

            self.tools[name] = tool
            logger.info(f"Registered tool: {name}")
        except Exception as e:
            logger.error(f"Error registering tool {name}: {str(e)}")
            raise

    def create_agent(
        self,
        system_prompt: str = None,
        doc_ids: list[str] = None,
        tool_names: list[str] = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> ReActAgent:
        """
        Create a ReActAgent with filters for tenant-specific knowledge

        Args:
            system_prompt: Optional system prompt for the agent
            doc_ids: Optional list of document IDs for tenant-specific filtering
            tool_names: List of tool names to include (None for all tools)
            temperature: Controls randomness (0.0 to 1.0); uses default if None
            max_tokens: Maximum token limit for responses; uses default if None

        Returns:
            ReActAgent instance
        """
        try:
            if doc_ids is not None:
                self.query_engine.set_doc_filter(doc_ids)
            else:
                self.query_engine.clear_doc_filter()

            self.tools["knowledge_search"] = self.query_engine.create_tool(
                name="knowledge_search",
                description=(
                    "Searches internal documentation to answer questions. "
                    "If no relevant documents are found, asks the user for more context. "
                    "The input should be a clear, concise, and specific question, optimized for retrieval-augmented generation."
                ),
                top_k=5,
            )

            agent_tools = self._prepare_tools(tool_names)
            system_prompt = system_prompt or self.default_system_prompt

            return ReActAgent.from_tools(
                tools=agent_tools,
                llm=self.get_llm(system_prompt, temperature, max_tokens),
                verbose=self.verbose,
                max_iterations=self.max_iterations,
            )
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            raise

    def _prepare_tools(self, tool_names: list[str] = None) -> list[BaseTool]:
        """
        Prepare the list of tools based on provided names

        Args:
            tool_names: List of tool names to include (None for all tools)

        Returns:
            List of BaseTool objects
        """
        if tool_names is None:
            logger.info("Using all registered tools")
            return list(self.tools.values())

        selected_tools = []
        for tool_name in tool_names:
            if tool_name in self.tools:
                selected_tools.append(self.tools[tool_name])
                logger.info(f"Added tool: {tool_name}")
            else:
                logger.warning(f"Tool {tool_name} not found, skipping")

        return selected_tools
