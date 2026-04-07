"""Performance metrics tracking for LLM calls and workflows"""
import time
from functools import wraps
from typing import Callable, Any
from contextlib import asynccontextmanager
from .logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Simple metrics collector for tracking performance"""

    def __init__(self):
        self.metrics = {}

    def track_llm_call(
        self,
        operation: str,
        duration_ms: float,
        tokens_used: int = 0,
        cache_hit: bool = False
    ):
        """Track LLM call metrics"""
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_duration_ms": 0,
                "total_tokens": 0,
                "cache_hits": 0,
                "avg_duration_ms": 0,
            }

        m = self.metrics[operation]
        m["count"] += 1
        m["total_duration_ms"] += duration_ms
        m["total_tokens"] += tokens_used
        if cache_hit:
            m["cache_hits"] += 1
        m["avg_duration_ms"] = m["total_duration_ms"] / m["count"]

    def get_metrics(self, operation: str = None) -> dict:
        """Get metrics for specific operation or all"""
        if operation:
            return self.metrics.get(operation, {})
        return self.metrics

    def reset(self):
        """Reset all metrics"""
        self.metrics = {}

    def log_summary(self):
        """Log metrics summary"""
        if not self.metrics:
            return

        logger.info("=== Performance Metrics Summary ===")
        for operation, m in self.metrics.items():
            cache_hit_rate = (m["cache_hits"] / m["count"] * 100) if m["count"] > 0 else 0
            logger.info(
                f"{operation}: {m['count']} calls, "
                f"avg {m['avg_duration_ms']:.2f}ms, "
                f"{m['total_tokens']} tokens, "
                f"{cache_hit_rate:.1f}% cache hits"
            )


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics_collector


def track_llm_latency(operation: str):
    """Decorator to track LLM call latency"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            cache_hit = False
            tokens_used = 0

            try:
                result = await func(*args, **kwargs)

                # Try to extract token usage from result
                if hasattr(result, 'raw'):
                    usage = getattr(result.raw, 'usage', None)
                    if usage:
                        tokens_used = getattr(usage, 'total_tokens', 0)

                # Check if result came from cache
                if isinstance(result, dict):
                    cache_hit = result.get('_from_cache', False)

                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                _metrics_collector.track_llm_call(
                    operation,
                    duration_ms,
                    tokens_used,
                    cache_hit
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                _metrics_collector.track_llm_call(operation, duration_ms, 0, False)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@asynccontextmanager
async def track_workflow_step(step_name: str):
    """Context manager to track workflow step duration"""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        logger.info(f"[PERF] {step_name}: {duration_ms:.2f}ms")


class WorkflowMetrics:
    """Track metrics for entire workflow execution"""

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.start_time = time.time()
        self.steps = []
        self.llm_calls = 0
        self.cache_hits = 0

    def add_step(self, step_name: str, duration_ms: float):
        """Add step timing"""
        self.steps.append({
            "name": step_name,
            "duration_ms": duration_ms
        })

    def increment_llm_calls(self, cache_hit: bool = False):
        """Increment LLM call counter"""
        self.llm_calls += 1
        if cache_hit:
            self.cache_hits += 1

    def finish(self) -> dict:
        """Finish tracking and return summary"""
        total_duration_ms = (time.time() - self.start_time) * 1000
        cache_hit_rate = (self.cache_hits / self.llm_calls * 100) if self.llm_calls > 0 else 0

        summary = {
            "workflow": self.workflow_name,
            "total_duration_ms": total_duration_ms,
            "llm_calls": self.llm_calls,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "steps": self.steps
        }

        logger.info(
            f"[WORKFLOW] {self.workflow_name}: {total_duration_ms:.2f}ms, "
            f"{self.llm_calls} LLM calls, {cache_hit_rate:.1f}% cache hits"
        )

        return summary
