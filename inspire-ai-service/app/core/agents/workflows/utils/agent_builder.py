"""DEPRECATED: Agent builder module - moved to assist_reply/agents/builder.py

This module is deprecated and maintained only for backward compatibility.
Please update imports to use the new location:

    from app.core.agents.workflows.assist_reply.agents.builder import (
        normalize_language,
        build_query_engine_tools,
        build_init_agent,
        build_topic_agents,
    )
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "Importing from 'app.core.agents.workflows.utils.agent_builder' is deprecated. "
    "Use 'from app.core.agents.workflows.assist_reply.agents.builder import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import and re-export all functions from new location
from app.core.agents.workflows.assist_reply.agents.builder import (
    normalize_language,
    build_query_engine_tools,
    build_init_agent,
    build_topic_agents,
)

__all__ = [
    "normalize_language",
    "build_query_engine_tools",
    "build_init_agent",
    "build_topic_agents",
]
