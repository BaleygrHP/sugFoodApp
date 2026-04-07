from fastapi import Depends, HTTPException
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.llms import ImageBlock

from app.core.agents.agent_manager import AgentManager
from app.core.tools.query_engine import QueryEngine
from app.core.logger import get_logger

logger = get_logger(__name__)


class AgentService:
    """Service for AI agent functionality without database dependencies"""

    def __init__(
        self,
        agent_manager: AgentManager = Depends(),
        query_engine: QueryEngine = Depends(),
    ):
        self.agent_manager = agent_manager
        self.query_engine = query_engine

    def ask_question(
        self,
        question: str,
        doc_ids: list[str] = None,
        system_prompt: str = None,
        chat_history: list[dict] = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Ask a question using the agent

        Args:
            question: User's question
            doc_ids: Optional list of document IDs to query from vector store
            system_prompt: Optional system instructions for the agent
            chat_history: Optional chat history for context
            temperature: Controls randomness (0.0 to 1.0); uses default if None
            max_tokens: Maximum response length; uses default if None
            use_react: Whether to use ReAct agent

        Returns:
            Dict with response and sources
        """
        system_prompt = system_prompt or self.agent_manager.default_system_prompt

        try:
            agent = self.agent_manager.create_agent(
                system_prompt=system_prompt,
                doc_ids=doc_ids,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize AI Agent")

        if chat_history and len(chat_history) > 0:
            chat_history = self._format_chat_history(chat_history)

        response_text = ""
        sources = []
        try:
            logger.info(f"Agent chat - question: {question[:100]}...")
            if chat_history:
                logger.debug(f"Agent chat - chat_history length: {len(chat_history)}")

            response = agent.chat(question, chat_history)
            logger.info(f"Agent response: {str(response)[:200]}...")

            if hasattr(response, "metadata") and response.metadata:
                tool_calls = response.metadata.get("tool_calls", [])
                for call in tool_calls:
                    if call.get("name") == "knowledge_search":
                        tool_response = call.get("response", {})
                        if isinstance(tool_response, dict) and "sources" in tool_response:
                            sources = tool_response["sources"]
                            logger.debug(f"Found {len(sources)} sources from knowledge_search")

        except Exception as e:
            if "max iterations" in str(e).lower() and hasattr(agent, "memory") and agent.memory:
                transcript = str(agent.memory)
                if "Answer:" in transcript:
                    last_answer = transcript.split("Answer:")[-1].strip()
                    response_text = last_answer
                    logger.info(f"Extracted partial response: {response_text[:100]}...")

                    return {
                        "answer": response_text,
                        "sources": sources,
                        "warning": "Agent reached maximum iterations but returned partial results.",
                    }

            logger.error(f"Error getting assistant response: {str(e)}")
            raise HTTPException(
                status_code=500, detail="AI assistant failed to generate a response"
            )

        return {"answer": str(response), "sources": sources}

    def _format_chat_history(self, history: list[dict]) -> list[ChatMessage]:
        """
        Format chat history for LlamaIndex ReActAgent consumption

        Supports multimodal messages with images for Gemini vision models.

        Args:
            history: Raw chat history from the client. Each message can include:
                - role: str (user/assistant/system)
                - content: str (text content)
                - images: list[dict] (optional list of images with url/base64)

        Returns:
            Formatted chat history for the agent
        """
        try:
            from app.settings import settings
            max_msgs = max(1, int(getattr(settings.llm, 'max_history_messages', 1)))
        except Exception:
            max_msgs = 1
        history = (history or [])[-max_msgs:]
        formatted_messages = []

        for msg in history:
            if "role" in msg and "content" in msg:
                role_str = msg["role"].lower()
                if role_str == "user":
                    role = MessageRole.USER
                elif role_str == "assistant":
                    role = MessageRole.ASSISTANT
                elif role_str == "system":
                    role = MessageRole.SYSTEM
                else:
                    logger.warning(f"Skipping message with unknown role: {role_str}")
                    continue

                content = msg["content"] if msg["content"] is not None else ""

                chat_msg = ChatMessage(role=role, content=content)

                if "images" in msg and msg["images"]:
                    images_data = []
                    for img in msg["images"]:
                        if isinstance(img, dict):
                            if img.get("url"):
                                chat_msg.blocks.append(ImageBlock(image_url=img["url"]))
                                images_data.append({"type": "image_url", "image_url": {"url": img["url"]}})
                            elif img.get("base64"):
                                mime_type = img.get("mime_type", "image/jpeg")
                                data_url = f"data:{mime_type};base64,{img['base64']}"
                                chat_msg.blocks.append(ImageBlock(image_url=data_url))
                                images_data.append({
                                    "type": "image_url",
                                    "image_url": {"url": data_url}
                                })

                    if images_data:
                        chat_msg.additional_kwargs = {"images": images_data}
                        try:
                            preview_urls = [i.get("image_url", {}).get("url", "")[:100] for i in images_data[:3]]
                            logger.info(f"Chat history: attached {len(images_data)} images to blocks and kwargs; preview={preview_urls}")
                        except Exception:
                            logger.info(f"Chat history: attached {len(images_data)} images")
                formatted_messages.append(chat_msg)

        return formatted_messages

    def query_knowledge(
        self,
        question: str,
        doc_ids: list = None,
        top_k: int = 5,
    ) -> dict:
        """
        Direct RAG query bypassing the agent

        This is more efficient for simple knowledge retrieval without
        complex reasoning steps.

        Args:
            question: Question to ask
            doc_ids: Optional list of document IDs to filter by
            top_k: Number of documents to retrieve

        Returns:
            Dict with answer, sources
        """
        try:
            logger.info(f"Processing direct RAG query: {question[:50]}...")

            if doc_ids:
                self.query_engine.set_doc_filter(doc_ids)
                logger.info(f"Set document filter with {len(doc_ids)} documents")
            else:
                self.query_engine.clear_doc_filter()
                logger.info("Using all documents (no filter)")

            result = self.query_engine.query(question, top_k=top_k)
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Handle empty or uninformative responses
            if not answer or answer.strip() == "" or "Empty Response" in answer:
                # If we have sources but no good answer, generate a response using the sources directly
                if sources:
                    logger.info("Empty response detected with available sources. Generating fallback response.")
                    context = "Based on the available information:\n\n"
                    for i, source in enumerate(sources, 1):
                        context += f"{i}. {source.get('text', '')}\n"

                    # Use a direct LLM call to generate a response from sources
                    system_prompt = """
You are a helpful knowledge assistant. When provided with information snippets, use them to answer the user's question.
If the information is not sufficient to fully answer the question, acknowledge that and provide what you can based on the given information.
Always respond with useful content - avoid saying 'I don't know' or 'No information provided'.
"""
                    llm = self.agent_manager.get_llm(system_prompt=system_prompt)
                    prompt = f"{context}\n\nUser question: {question}\n\nPlease answer this question based on the provided information snippets."
                    response = llm.complete(prompt)
                    answer = response.text
                else:
                    # No sources found - provide a helpful fallback response
                    logger.warning(f"No relevant documents found for query: '{question}'")
                    system_prompt = "You are a helpful assistant. When you don't have specific information, provide a general helpful response."
                    llm = self.agent_manager.get_llm(system_prompt=system_prompt)
                    prompt = f"The user asked: {question}\n\nI don't have specific information about this in my knowledge base. Please provide a helpful general response that acknowledges this limitation while still being as helpful as possible."
                    response = llm.complete(prompt)
                    answer = response.text

            return {
                "answer": answer,
                "sources": sources,
            }

        except Exception as e:
            logger.error(f"Error in direct knowledge query: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error querying knowledge base: {str(e)}"
            )

    def complete_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Pure LLM completion without RAG or agent

        For direct prompting scenarios where knowledge retrieval isn't needed.

        Args:
            prompt: Text prompt to complete
            system_prompt: Optional system instructions
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum token length for response

        Returns:
            Dict with completion
        """
        try:
            logger.info(f"Processing LLM completion: {prompt[:50]}...")

            if system_prompt is None:
                system_prompt = "You are a helpful AI assistant. Provide accurate and concise information."

            llm = self.agent_manager.get_llm(system_prompt, temperature, max_tokens)
            logger.debug(f"LLM completion - prompt: {prompt[:100]}...")
            logger.debug(f"LLM completion - system_prompt: {system_prompt[:100]}...")

            response = llm.complete(prompt)
            logger.info(f"LLM completion response: {response.text[:200]}...")

            return response.text

        except Exception as e:
            logger.error(f"Error in LLM completion: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error completing prompt: {str(e)}"
            )

    def complete_with_chat_history(
        self,
        prompt: str = None,
        chat_history: list[dict] = None,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Complete a prompt with chat history

        Uses the LLM's chat capabilities directly without RAG or agent reasoning.

        Args:
            prompt: Current prompt to respond to
            chat_history: Previous chat messages
            system_prompt: Optional system instructions
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum token length for response

        Returns:
            Dict with completion
        """
        try:
            logger.info(f"Processing chat completion: {prompt[:50]}...")

            if system_prompt is None:
                system_prompt = (
                    "You are a helpful AI assistant. Provide accurate and concise information."
                )

            llm = self.agent_manager.get_llm(system_prompt, temperature, max_tokens)

            messages = []
            if chat_history and len(chat_history) > 0:
                history_messages = self._format_chat_history(chat_history)
                messages.extend(history_messages)
                logger.debug(f"Chat completion - chat_history length: {len(history_messages)}")

            if prompt:
                messages.append(ChatMessage(role=MessageRole.USER, content=prompt))
                logger.info(f"Chat completion - prompt: {prompt[:100]}...")

            logger.debug(f"Chat completion - system_prompt: {system_prompt[:100]}...")
            response = llm.chat(messages)

            response_text = (
                response.message.content
                if hasattr(response, "message")
                else str(response)
            )
            logger.info(f"Chat completion response: {response_text[:200]}...")

            return response_text

        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error completing chat: {str(e)}"
            )

    def enhanced_chat_complete(
        self,
        prompt: str = None,
        chat_history: list[dict] = None,
        system_prompt: str = None,
        use_knowledge: bool = True,
        top_k: int = 3,
        doc_ids: list[str] = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Enhanced chat completion combining RAG and chat history with token tracking

        Args:
            prompt: Current prompt to respond to
            chat_history: Previous chat messages
            system_prompt: Optional system instructions
            use_knowledge: Whether to use RAG to enhance response
            top_k: Number of knowledge pieces to retrieve
            doc_ids: Optional list of document IDs to filter by
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum token length for response

        Returns:
            Dict with completion, sources
        """
        try:
            if system_prompt is None:
                system_prompt = (
                    "You are a helpful AI assistant. When provided with specific information, "
                    "base your answers on that information. If no specific information is "
                    "provided, use your own knowledge to give the best possible answer."
                    "Use a natural, conversational style with occasional contractions (like 'don't' instead of 'do not'). "
                    "Vary your sentence structure and length. When appropriate, use analogies or examples to explain complex topics."
                )

            knowledge_context = ""
            sources = []
            knowledge_prompt = ""

            # Retrieve relevant knowledge if requested
            if use_knowledge and prompt:
                current_question = prompt

                if doc_ids:
                    self.query_engine.set_doc_filter(doc_ids)
                else:
                    self.query_engine.clear_doc_filter()

                knowledge_result = self.query_engine.query(current_question, top_k=top_k, extract_full=True)
                sources = knowledge_result.get("sources", [])

                if sources:
                    knowledge_context = "Based on the following information:\n\n"
                    for i, source in enumerate(sources, 1):
                        knowledge_context += f"{i}. {source['text']}\n"
                    knowledge_context += "\n"

                    knowledge_prompt = (
                        f"{knowledge_context}"
                        f"Please consider this information for your response. "
                        f"If this information doesn't fully address the user's question, "
                        f"feel free to supplement with your own knowledge while clearly indicating which parts "
                        f"are based on the provided information versus your general knowledge."
                    )

            llm = self.agent_manager.get_llm(system_prompt, temperature, max_tokens)

            # Format chat history
            messages = []
            if chat_history and len(chat_history) > 0:
                history_messages = self._format_chat_history(chat_history)
                messages.extend(history_messages)

            # Add knowledge context and current prompt
            if prompt:
                if knowledge_prompt and use_knowledge:
                    full_prompt = f"{knowledge_prompt}\n\nUser question: {prompt}"
                    messages.append(ChatMessage(role=MessageRole.USER, content=full_prompt))
                else:
                    messages.append(ChatMessage(role=MessageRole.USER, content=prompt))

            # Generate response
            logger.debug(f"Enhanced chat - total messages: {len(messages)}")
            response = llm.chat(messages)
            response_text = response.message.content if hasattr(response, "message") else str(response)
            logger.info(f"Enhanced chat response: {response_text[:200]}...")

            return response_text

        except Exception as e:
            logger.error(f"Error in enhanced chat completion: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error completing enhanced chat: {str(e)}"
            )
