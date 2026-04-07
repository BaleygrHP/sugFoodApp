"""DEPRECATED: Parallel executor module - moved to assist_reply/agents/executor.py

This module is deprecated and maintained only for backward compatibility.
Please update imports to use the new location:

    from app.core.agents.workflows.assist_reply.agents.executor import execute_agents_parallel
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "Importing from 'app.core.agents.workflows.utils.parallel_executor' is deprecated. "
    "Use 'from app.core.agents.workflows.assist_reply.agents.executor import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import and re-export from new location
from app.core.agents.workflows.assist_reply.agents.executor import execute_agents_parallel

__all__ = ["execute_agents_parallel"]
