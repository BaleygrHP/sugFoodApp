from fastapi import APIRouter, Depends

from app.schemas.agent import QuestionDto, DirectQueryDto, CompletionDto, ChatCompletionDto, EnhancedChatCompletionDto
from app.services.agent import AgentService

agent_router = router = APIRouter(prefix="/agent")


@router.post("/ask-question", response_model=dict)
def ask_agent(body: QuestionDto, service: AgentService = Depends()):
    """
    Ask a question with ReAct agent (complex reasoning, tool use)

    This approach uses a ReAct agent that can use tools and reason step-by-step.
    Most powerful but uses more tokens.

    - question: The question to ask
    - doc_ids: List of document IDs to search in (optional)
    - system_prompt: Optional system instructions for the agent
    - chat_history: Previous conversation history (optional)
    - temperature: Controls randomness (0.0 to 1.0)
    - max_tokens: Maximum response length

    Returns the answer along with source information.
    """
    return service.ask_question(
        question=body.question,
        doc_ids=body.doc_ids,
        system_prompt=body.system_prompt,
        chat_history=body.chat_history,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )


@router.post("/rag-query", response_model=dict)
async def direct_rag_query(
    body: DirectQueryDto, agent_service: AgentService = Depends()
):
    """
    Direct RAG query bypassing the agent

    Faster for simple knowledge retrieval without complex reasoning
    """
    return agent_service.query_knowledge(
        question=body.question, doc_ids=body.doc_ids, top_k=body.top_k
    )


@router.post("/complete", response_model=str)
async def llm_completion(
    body: CompletionDto, agent_service: AgentService = Depends()
):
    """
    Pure LLM completion without RAG or agent

    For direct prompting without knowledge retrieval
    """
    return agent_service.complete_prompt(
        prompt=body.prompt,
        system_prompt=body.system_prompt,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )


@router.post("/chat-complete", response_model=str)
async def llm_chat_completion(
    body: ChatCompletionDto, agent_service: AgentService = Depends(),
):
    """
    Chat completion with history support

    Uses the LLM directly with chat history, without RAG or agent

    - prompt: The current message to respond to
    - chat_history: Previous conversation messages
    - system_prompt: Instructions for the LLM
    - temperature: Controls randomness (0.0 to 1.0)
    - max_tokens: Maximum response length
    """
    return agent_service.complete_with_chat_history(
        prompt=body.prompt,
        chat_history=body.messages,
        system_prompt=body.system_prompt,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )


@router.post("/enhanced-chat-complete", response_model=str)
async def enhanced_chat_completion(
    body: EnhancedChatCompletionDto, agent_service: AgentService = Depends()
):
    """
    Enhanced chat completion combining RAG and chat history

    This endpoint combines knowledge retrieval with chat capabilities:
    - Retrieves relevant knowledge from the vector store
    - Integrates chat history for context maintenance
    - Returns generated response with sources
    """
    return agent_service.enhanced_chat_complete(
        prompt=body.prompt,
        chat_history=body.messages,
        system_prompt=body.system_prompt,
        use_knowledge=body.use_knowledge,
        top_k=body.top_k,
        doc_ids=body.doc_ids,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
