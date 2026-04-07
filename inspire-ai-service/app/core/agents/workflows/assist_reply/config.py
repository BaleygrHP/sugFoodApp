"""Configuration module for AssistReply workflow.

This module centralizes all workflow configuration constants, making them
configurable via environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class WorkflowConfig:
    """Centralized configuration for AssistReply workflow.

    All configuration values can be overridden via environment variables.
    Default values are provided for each setting.

    Attributes:
        parallel_agent_timeout: Maximum seconds to wait for each agent in parallel execution
        knowledge_timeout: Maximum seconds for knowledge base queries
        knowledge_top_k: Number of top results to retrieve from knowledge base
        llm_timeout: Maximum seconds for LLM response generation
        max_retry_attempts: Maximum retry attempts for transient failures
        retry_backoff_base: Base backoff time in seconds for exponential backoff
        max_image_attach: Maximum number of images to attach to prompts
    """

    parallel_agent_timeout: float = 60.0  # seconds
    knowledge_timeout: float = 15.0  # seconds
    knowledge_top_k: int = 5  # top-K retrieval
    llm_timeout: float = 30.0  # seconds
    max_retry_attempts: int = 2  # retry count
    retry_backoff_base: float = 1.0  # seconds
    max_image_attach: int = 5  # max images in prompt
    max_agent_iterations: int = 10  # max tool calls per agent (prevents infinite loops)

    # Singleton instance
    _instance: ClassVar['WorkflowConfig | None'] = None

    @classmethod
    def from_env(cls) -> 'WorkflowConfig':
        """Load configuration from environment variables with defaults.

        Environment variables:
            WORKFLOW__PARALLEL_AGENT_TIMEOUT: Agent execution timeout (default: 60.0)
            WORKFLOW__KNOWLEDGE_TIMEOUT: Knowledge query timeout (default: 15.0)
            WORKFLOW__KNOWLEDGE_TOP_K: Top-K retrieval count (default: 5)
            WORKFLOW__LLM_TIMEOUT: LLM generation timeout (default: 30.0)
            WORKFLOW__MAX_RETRY_ATTEMPTS: Retry attempts (default: 2)
            WORKFLOW__RETRY_BACKOFF_BASE: Backoff base time (default: 1.0)
            WORKFLOW__MAX_IMAGE_ATTACH: Max images in prompt (default: 5)
            WORKFLOW__MAX_AGENT_ITERATIONS: Max tool calls per agent (default: 10)

        Returns:
            WorkflowConfig instance with values from environment or defaults
        """
        return cls(
            parallel_agent_timeout=float(os.getenv("WORKFLOW__PARALLEL_AGENT_TIMEOUT", "60.0")),
            knowledge_timeout=float(os.getenv("WORKFLOW__KNOWLEDGE_TIMEOUT", "15.0")),
            knowledge_top_k=int(os.getenv("WORKFLOW__KNOWLEDGE_TOP_K", "5")),
            llm_timeout=float(os.getenv("WORKFLOW__LLM_TIMEOUT", "30.0")),
            max_retry_attempts=int(os.getenv("WORKFLOW__MAX_RETRY_ATTEMPTS", "2")),
            retry_backoff_base=float(os.getenv("WORKFLOW__RETRY_BACKOFF_BASE", "1.0")),
            max_image_attach=int(os.getenv("WORKFLOW__MAX_IMAGE_ATTACH", "5")),
            max_agent_iterations=int(os.getenv("WORKFLOW__MAX_AGENT_ITERATIONS", "10")),
        )

    @classmethod
    def get_instance(cls) -> 'WorkflowConfig':
        """Get or create singleton instance of WorkflowConfig.

        Returns:
            Singleton WorkflowConfig instance
        """
        if cls._instance is None:
            cls._instance = cls.from_env()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.parallel_agent_timeout <= 0:
            raise ValueError(f"parallel_agent_timeout must be > 0, got {self.parallel_agent_timeout}")

        if self.knowledge_timeout <= 0:
            raise ValueError(f"knowledge_timeout must be > 0, got {self.knowledge_timeout}")

        if self.knowledge_top_k <= 0:
            raise ValueError(f"knowledge_top_k must be > 0, got {self.knowledge_top_k}")

        if self.llm_timeout <= 0:
            raise ValueError(f"llm_timeout must be > 0, got {self.llm_timeout}")

        if self.max_retry_attempts < 0:
            raise ValueError(f"max_retry_attempts must be >= 0, got {self.max_retry_attempts}")

        if self.retry_backoff_base <= 0:
            raise ValueError(f"retry_backoff_base must be > 0, got {self.retry_backoff_base}")

        if self.max_image_attach < 0:
            raise ValueError(f"max_image_attach must be >= 0, got {self.max_image_attach}")

        if self.max_agent_iterations <= 0:
            raise ValueError(f"max_agent_iterations must be > 0, got {self.max_agent_iterations}")


# Global configuration instance (lazy-loaded)
def get_config() -> WorkflowConfig:
    """Get global workflow configuration instance.

    Returns:
        WorkflowConfig singleton instance
    """
    return WorkflowConfig.get_instance()
