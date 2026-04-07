import asyncio
import json
import time
from typing import List

from llama_index.core.agent.workflow import FunctionAgent, AgentWorkflow, AgentOutput, ToolCall, ToolCallResult
from llama_index.core.llms import ChatMessage

from app.core.logger import get_logger
from app.core.agents.workflows.utils.retry import retry_on_transient_error

logger = get_logger(__name__)


async def execute_agents_parallel(
    agents: List[FunctionAgent],
    chat_history: List[ChatMessage],
    timeout_per_agent: float = 30.0,
) -> List[str]:
    """
    Execute multiple agents in parallel and collect their outputs.

    This function runs agents concurrently to reduce total response time.
    Individual agent failures or timeouts do not affect other agents.

    Args:
        agents: List of FunctionAgent instances to run in parallel
        chat_history: Conversation context to provide to each agent
        timeout_per_agent: Maximum seconds to wait for each agent (default: 30s)

    Returns:
        List of agent output strings. Empty strings for failed/timed-out agents.

    Example:
        >>> agents = [booking_agent, payment_agent, support_agent]
        >>> outputs = await execute_agents_parallel(agents, chat_history)
        >>> valid_outputs = [out for out in outputs if out.strip()]
    """
    if not agents:
        return []

    overall_start = time.perf_counter()
    logger.info(f"[SubAgent] Parallel execution: agents={len(agents)} messages={len(chat_history)}")
    try:
        names = [getattr(a, 'name', f'Agent-{i}') for i, a in enumerate(agents)]
        logger.info(f"[SubAgent] Agents: {names}")
    except Exception:
        pass

    try:
        def _truncate(v: str, n: int = 500) -> str:
            return v if len(v) <= n else v[:n] + "…"

        preview = []
        for m in chat_history[:5]:
            role = getattr(m, 'role', None) or getattr(m, 'message_type', None)
            content = getattr(m, 'content', '') or ''
            preview.append({"role": str(role), "content": _truncate(str(content), 300)})
        logger.info(f"[SubAgent] Chat preview: {json.dumps(preview, ensure_ascii=False)}")
    except Exception:
        pass

    async def run_single_agent(agent: FunctionAgent, index: int) -> str:
        """Execute a single agent with timeout, error handling, and retry logic.

        Transient errors (network, timeout) will be automatically retried with
        exponential backoff. Non-retryable errors (validation) fail fast.
        """
        agent_name = getattr(agent, "name", f"Agent-{index}")

        # Wrapper function for retry logic
        @retry_on_transient_error()
        async def execute_agent_with_retry():
            """Inner function that executes the agent and can be retried."""
            return await _execute_agent_core(agent, agent_name, timeout_per_agent)

        try:
            return await execute_agent_with_retry()
        except Exception as e:
            # All errors (after retries exhausted) are caught here
            duration = time.perf_counter() - time.perf_counter()  # Will be updated in _execute_agent_core
            logger.error(
                f"[SubAgent] {agent_name} failed after all retry attempts: "
                f"{type(e).__name__}: {str(e)[:200]}"
            )
            return {
                "status": "error",
                "content": "",
                "partial_content": "",
                "duration": 0.0,
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def _execute_agent_core(agent: FunctionAgent, agent_name: str, timeout: float) -> dict:
        """Core agent execution logic (separated for retry wrapping)."""
        content_parts = []

        try:
            start_ts = time.perf_counter()
            logger.info(f"[SubAgent] Starting agent: {agent_name}")

            try:
                def _local_trunc(v: object, n: int = 1000) -> str:
                    try:
                        s = str(v) if v is not None else ""
                        return s if len(s) <= n else s[:n] + "…"
                    except Exception:
                        return "<unprintable>"

                agent_desc = getattr(agent, 'description', '')
                agent_sys_prompt = getattr(agent, 'system_prompt', '')
                logger.debug(f"[SubAgent] {agent_name} description: {agent_desc}")
                logger.debug(f"[SubAgent] {agent_name} system_prompt: { _local_trunc(agent_sys_prompt) }")
            except Exception:
                pass

            # Wrap agent in AgentWorkflow for proper async execution
            agent_workflow = AgentWorkflow(
                agents=[agent],
                root_agent=agent.name,
                initial_state={},
            )

            logger.info(f"[SubAgent] {agent_name} - messages={len(chat_history)} tools={len(getattr(agent, 'tools', []))}")

            # Run agent workflow and collect output
            handler = agent_workflow.run(chat_history=chat_history.copy())

            content_parts = []
            async def collect_output():
                current_agent = None
                try:
                    async for event in handler.stream_events():
                        if (
                            hasattr(event, "current_agent_name")
                            and event.current_agent_name != current_agent
                        ):
                            current_agent = event.current_agent_name
                            logger.info(f"[SubAgent] -> {agent_name} switched to node: {current_agent}")
                            continue

                        if isinstance(event, AgentOutput):
                            content_text = getattr(event.response, "content", "") or ""
                            if content_text:
                                content_parts.append(content_text)
                                logger.info(f"[SubAgent] {agent_name} output chunk: {len(content_text)} chars")
                            if getattr(event, "tool_calls", None):
                                planned = [call.tool_name for call in event.tool_calls]
                                logger.info(f"[SubAgent] {agent_name} planning tools: {planned}")
                            continue

                        if isinstance(event, ToolCall):
                            try:
                                tool_name = event.tool_name
                                logger.info(f"[SubAgent] {agent_name} calling tool: {tool_name}")
                                try:
                                    kwargs = getattr(event, 'tool_kwargs', {}) or {}

                                    # Log HTTP tool calls with more detail
                                    method = kwargs.get('method') or kwargs.get('http_method')
                                    url = kwargs.get('url') or kwargs.get('endpoint')
                                    if method and url:
                                        # Extract body/json data for logging (masked)
                                        body_data = kwargs.get('json') or kwargs.get('data') or {}
                                        params_data = kwargs.get('params') or {}

                                        def truncate(val, max_len=200):
                                            s = str(val)
                                            return s if len(s) <= max_len else s[:max_len] + "..."

                                        logger.info(
                                            f"[SubAgent] {agent_name} HTTP {method} {url} | "
                                            f"params={truncate(params_data)} | body_keys={list(body_data.keys()) if isinstance(body_data, dict) else 'N/A'}"
                                        )
                                    else:
                                        # Non-HTTP tool call
                                        keys = list(kwargs.keys())
                                        # Log first few values for debugging
                                        preview = {k: str(v)[:100] for k, v in list(kwargs.items())[:3]}
                                        logger.info(f"[SubAgent] {agent_name} tool kwargs: {preview}")
                                except Exception as e:
                                    logger.warning(f"[SubAgent] {agent_name} error logging tool details: {e}")

                            except Exception as e:
                                logger.error(f"[SubAgent] {agent_name} error logging tool call: {e}")
                                logger.debug(f"[SubAgent] {agent_name} tool call")
                            continue

                        if isinstance(event, ToolCallResult):
                            try:
                                tool_name = event.tool_name
                                tool_output = event.tool_output

                                size_hint = None
                                try:
                                    if isinstance(tool_output, (str, bytes)):
                                        size_hint = len(tool_output)
                                    else:
                                        size_hint = len(json.dumps(tool_output))
                                except Exception:
                                    size_hint = None

                                logger.info(f"[SubAgent] {agent_name} tool result: {tool_name} size={size_hint}")

                            except Exception as e:
                                logger.error(f"[SubAgent] {agent_name} error logging tool result: {e}")
                                logger.info(f"[SubAgent] {agent_name} tool result (unprintable)")
                            continue

                        if hasattr(event, 'response') and hasattr(event.response, 'content'):
                            if event.response.content:
                                content_parts.append(event.response.content)
                except StopAsyncIteration:
                    return
                except Exception as e:
                    logger.warning(f"[SubAgent] {agent_name} stream aborted: {type(e).__name__}: {e}")
                    return

            try:
                await asyncio.wait_for(
                    collect_output(),
                    timeout=timeout
                )
            except StopAsyncIteration:
                pass
            except Exception as e:
                logger.warning(f"[SubAgent] {agent_name} wait_for aborted: {type(e).__name__}: {e}")

            content = " ".join(content_parts) if content_parts else ""

            if content:
                duration = time.perf_counter() - start_ts
                logger.info(f"Agent {agent_name} completed: {len(content)} chars in {duration:.3f}s")
                # Return structured success result
                return {"status": "success", "content": content, "duration": duration}
            else:
                logger.warning(f"Agent {agent_name} returned empty content")
                # Return structured empty result (not an error)
                return {"status": "empty", "content": "", "duration": time.perf_counter() - start_ts}

        except asyncio.TimeoutError:
            duration = time.perf_counter() - start_ts
            logger.warning(f"Agent {agent_name} timed out after {timeout}s")
            # Preserve partial results even on timeout
            partial_content = " ".join(content_parts) if content_parts else ""
            # Timeout errors are transient and will be retried by the retry wrapper
            raise asyncio.TimeoutError(f"Agent {agent_name} timed out after {timeout}s")
        except Exception as e:
            duration = time.perf_counter() - start_ts
            logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
            # Re-raise to let retry logic handle transient vs non-transient errors
            raise

    # Create tasks for all agents
    tasks = [run_single_agent(agent, idx) for idx, agent in enumerate(agents)]

    # Execute all tasks concurrently
    logger.info(f"Executing {len(agents)} agents in parallel")
    outputs = await asyncio.gather(*tasks, return_exceptions=True)

    # Process structured results and extract content
    clean_outputs = []
    stats = {"success": 0, "empty": 0, "timeout": 0, "error": 0}

    for idx, output in enumerate(outputs):
        agent_name = getattr(agents[idx], "name", f"Agent-{idx}")

        if isinstance(output, Exception):
            # Shouldn't happen with error handling above, but handle gracefully
            logger.error(f"Unexpected exception from {agent_name}: {output}")
            clean_outputs.append("")
            stats["error"] += 1
        elif isinstance(output, dict):
            # Structured result format
            status = output.get("status", "unknown")
            content = output.get("content", "")
            partial = output.get("partial_content", "")

            stats[status] = stats.get(status, 0) + 1

            if status == "success":
                clean_outputs.append(content)
            elif status in ("timeout", "error") and partial:
                # Use partial results if available
                logger.info(f"Using partial result from {agent_name}: {len(partial)} chars")
                clean_outputs.append(partial)
            else:
                clean_outputs.append("")
        else:
            # Fallback: treat as string (backward compatibility)
            clean_outputs.append(str(output) if output else "")
            if output:
                stats["success"] += 1

    successful_count = sum(1 for out in clean_outputs if out.strip())
    total_chars = sum(len(o) for o in clean_outputs if isinstance(o, str))
    overall_duration = time.perf_counter() - overall_start

    logger.info(
        f"[SubAgent] Completed in {overall_duration:.3f}s | "
        f"Results: {successful_count}/{len(agents)} with content | "
        f"Status breakdown: {stats} | "
        f"Total chars: {total_chars}"
    )

    return clean_outputs
