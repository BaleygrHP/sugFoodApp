from llama_index.core import Settings as LlamaIndexSettings
from llama_index.llms.gemini import Gemini

from app.settings import settings
from app.settings.llm import Provider


def configure_llm():
    provider = settings.llm.provider

    if provider == Provider.GEMINI:
        from llama_index.embeddings.gemini import GeminiEmbedding

        LlamaIndexSettings.llm = Gemini(
            model=f"models/{settings.llm.gemini.model_name or 'gemini-2.0-flash-lite'}",
            api_key=settings.llm.gemini.api_key,
            temperature=settings.llm.gemini.temperature or 0.7,
            max_tokens=settings.llm.gemini.max_tokens or 8192,
        )
        LlamaIndexSettings.agentic_llm = Gemini(
            model=f"models/{settings.llm.agentic_gemini.model_name or 'gemini-2.5-flash-preview-05-20'}",
            api_key=settings.llm.gemini.api_key,
            temperature=settings.llm.agentic_gemini.temperature or 0.7,
            max_tokens=settings.llm.agentic_gemini.max_tokens or 8192,
        )
        # Tool-specific LLM with temperature=0.0 for deterministic tool execution
        LlamaIndexSettings.tool_llm = Gemini(
            model=f"models/{settings.llm.agentic_gemini.model_name or 'gemini-2.5-flash-preview-05-20'}",
            api_key=settings.llm.gemini.api_key,
            temperature=settings.llm.agentic_gemini.tool_execution_temperature,
            max_tokens=settings.llm.agentic_gemini.max_tokens or 8192,
        )
        LlamaIndexSettings.embed_model = GeminiEmbedding(
            model_name=f"models/{settings.llm.gemini.embed_model or 'text-embedding-004'}", api_key=settings.llm.gemini.api_key
        )
    elif provider == Provider.OPENAI:
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI

        LlamaIndexSettings.llm = OpenAI(
            model=settings.llm.openai.model_name or "gpt-3.5-turbo",
            api_key=settings.llm.openai.api_key,
            temperature=settings.llm.openai.temperature or 0.7,
            max_tokens=settings.llm.openai.max_tokens or 1000,
        )
        LlamaIndexSettings.agentic_llm = LlamaIndexSettings.llm
        # Tool-specific LLM with temperature=0.0 for deterministic tool execution
        LlamaIndexSettings.tool_llm = OpenAI(
            model=settings.llm.openai.model_name or "gpt-3.5-turbo",
            api_key=settings.llm.openai.api_key,
            temperature=settings.llm.openai.tool_execution_temperature,
            max_tokens=settings.llm.openai.max_tokens or 1000,
        )
        LlamaIndexSettings.embed_model = OpenAIEmbedding(
            model=settings.llm.openai.embed_model or "text-embedding-004",
            api_key=settings.llm.openai.api_key,
            embedding_dimensions=settings.llm.openai.embedding_dimensions or 1536,
        )

    LlamaIndexSettings.chunk_size = settings.llm.index.chunk_size
    LlamaIndexSettings.chunk_overlap = settings.llm.index.chunk_overlap

    try:
        from app.core.token_tracking import setup_token_tracking
        setup_token_tracking()
    except Exception:
        # Token tracking is optional, so we can ignore any errors here
        pass
