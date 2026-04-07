"""Retry logic for tool execution with configurable backoff.

This module provides retry decorators and utilities for handling transient failures
in tool execution. Only network and timeout errors are retried; validation errors
fail fast without retry.
"""

import asyncio
from functools import wraps
from typing import Callable, TypeVar, Any
import os

from app.core.logger import get_logger

logger = get_logger(__name__)

# Type variable for generic return types
T = TypeVar('T')

# Transient errors that should be retried
TRANSIENT_ERRORS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,  # Network-related OS errors
    # Add aiohttp.ClientError if using aiohttp
)

# Non-retryable errors that should fail fast
NON_RETRYABLE_ERRORS = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should be retried.

    Args:
        error: The exception to check

    Returns:
        True if error is transient (network, timeout), False otherwise
    """
    # Check for explicit non-retryable errors
    if isinstance(error, NON_RETRYABLE_ERRORS):
        return False

    # Check for transient errors
    if isinstance(error, TRANSIENT_ERRORS):
        return True

    # Check for validation errors (custom exception names)
    error_type_name = type(error).__name__
    if 'Validation' in error_type_name or 'Schema' in error_type_name:
        return False

    # Default: don't retry unknown errors
    return False


def retry_on_transient_error(
    max_attempts: int | None = None,
    backoff_base: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries async functions on transient errors with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts (default from env or 2)
        backoff_base: Base backoff time in seconds (default from env or 1.0)

    Usage:
        @retry_on_transient_error(max_attempts=3, backoff_base=1.0)
        async def my_function():
            # Function code that may fail transiently
            pass
    """
    # Load from environment with defaults
    if max_attempts is None:
        max_attempts = int(os.getenv("WORKFLOW__MAX_RETRY_ATTEMPTS", "2"))
    if backoff_base is None:
        backoff_base = float(os.getenv("WORKFLOW__RETRY_BACKOFF_BASE", "1.0"))

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # Check if error is retryable
                    if not is_transient_error(e):
                        logger.info(
                            f"[Retry] {func.__name__} failed with non-retryable error: "
                            f"{type(e).__name__}: {str(e)[:100]}"
                        )
                        raise

                    # Don't retry on last attempt
                    if attempt >= max_attempts:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {max_attempts} attempts: "
                            f"{type(e).__name__}: {str(e)[:200]}"
                        )
                        raise

                    # Calculate exponential backoff: backoff_base * (2 ^ (attempt - 1))
                    # attempt=1: 1s, attempt=2: 2s, attempt=3: 4s, etc.
                    backoff_time = backoff_base * (2 ** (attempt - 1))

                    logger.warning(
                        f"[Retry] {func.__name__} failed, retrying (attempt {attempt}/{max_attempts}): "
                        f"{type(e).__name__}: {str(e)[:100]} | "
                        f"Waiting {backoff_time}s before retry"
                    )

                    await asyncio.sleep(backoff_time)

            # Should never reach here, but just in case
            if last_error:
                raise last_error
            raise RuntimeError(f"{func.__name__} failed with unknown error")

        return wrapper
    return decorator


async def retry_agent_execution(
    agent_name: str,
    tool_name: str,
    execution_func: Callable[[], T],
    max_attempts: int | None = None,
    backoff_base: float | None = None,
) -> T:
    """Retry agent tool execution with logging specific to agents.

    This is a specialized retry function for agent tool execution that provides
    detailed logging with agent and tool names.

    Args:
        agent_name: Name of the agent executing the tool
        tool_name: Name of the tool being executed
        execution_func: Async function to execute (should be parameterless)
        max_attempts: Maximum retry attempts (default from env or 2)
        backoff_base: Base backoff time in seconds (default from env or 1.0)

    Returns:
        Result from execution_func

    Raises:
        Exception: If all retry attempts fail or non-retryable error occurs
    """
    if max_attempts is None:
        max_attempts = int(os.getenv("WORKFLOW__MAX_RETRY_ATTEMPTS", "2"))
    if backoff_base is None:
        backoff_base = float(os.getenv("WORKFLOW__RETRY_BACKOFF_BASE", "1.0"))

    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await execution_func()
        except Exception as e:
            last_error = e

            # Check if error is retryable
            if not is_transient_error(e):
                logger.info(
                    f"[Retry] Agent '{agent_name}' tool '{tool_name}' failed with non-retryable error: "
                    f"{type(e).__name__}: {str(e)[:100]}"
                )
                raise

            # Don't retry on last attempt
            if attempt >= max_attempts:
                logger.error(
                    f"[Retry] Agent '{agent_name}' tool '{tool_name}' failed after {max_attempts} attempts: "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                raise

            # Calculate exponential backoff
            backoff_time = backoff_base * (2 ** (attempt - 1))

            logger.warning(
                f"[Retry] Agent '{agent_name}' tool '{tool_name}' failed, retrying (attempt {attempt}/{max_attempts}): "
                f"{type(e).__name__}: {str(e)[:100]} | "
                f"Waiting {backoff_time}s before retry"
            )

            await asyncio.sleep(backoff_time)

    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError(f"Agent '{agent_name}' tool '{tool_name}' failed with unknown error")
