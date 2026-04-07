import json
import os
from datetime import datetime
from pathlib import Path

from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler


class TokenTracker:
    """Token tracking utility for monitoring and reporting token usage"""

    def __init__(self, log_to_file: bool = True, log_directory: str = "logs/tokens"):
        """
        Initialize the token tracker

        Args:
            log_to_file: Whether to log token usage to file
            log_directory: Directory for token usage logs
        """
        self.token_counter = TokenCountingHandler()
        self.log_to_file = log_to_file
        self.log_directory = log_directory
        if log_to_file:
            os.makedirs(log_directory, exist_ok=True)

    def setup_callback_manager(self) -> CallbackManager:
        """Set up callback manager with token counter and return it"""
        return CallbackManager(handlers=[self.token_counter])

    def get_token_counts(self) -> dict[str, dict[str, int]]:
        """Get current token counts from the handler"""
        return {
            "prompt": {
                "total": self.token_counter.prompt_llm_token_count,
                "completion": self.token_counter.completion_llm_token_count,
                "total_count": (
                    self.token_counter.prompt_llm_token_count
                    + self.token_counter.completion_llm_token_count
                ),
            },
            "embedding": {
                "total": self.token_counter.total_embedding_token_count,
            },
        }

    def get_total_token_count(self) -> int:
        """Get the total token count (prompt + completion + embedding)"""
        counts = self.get_token_counts()
        return counts["prompt"]["total_count"] + counts["embedding"]["total"]

    def reset_counts(self) -> None:
        """Reset all token counts to zero"""
        self.token_counter.reset_counts()

    def log_token_usage(self, context: dict[str, any] | None = None) -> dict:
        """
        Log token usage and return the data
        """
        token_data = self.get_token_counts()

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "tokens": token_data,
            "context": context or {},
        }

        if self.log_to_file:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = Path(self.log_directory) / f"token-usage-{date_str}.log"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data) + "\n")

        return log_data

    def export_to_json(self, filepath: str) -> None:
        """
        Export current token usage to a JSON file

        Args:
            filepath: Path to save the JSON file
        """
        token_data = self.get_token_counts()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

    def print_call_summary(
        self, call_info: dict, additional_context: dict | None = None
    ):
        """
        Print a formatted summary of token usage for a call

        Args:
            call_info: Information returned from track_call_tokens
            additional_context: Additional context to include in the summary
        """
        current_counts = self.get_session_token_count()

        print(f"\n🔢 Token Usage Summary for '{call_info['call_name']}':")
        print(f"   📝 Prompt tokens: {current_counts['prompt_tokens']:,}")
        print(f"   🤖 Completion tokens: {current_counts['completion_tokens']:,}")
        print(f"   📊 Embedding tokens: {current_counts['embedding_tokens']:,}")
        print(f"   💯 Total tokens (this call): {current_counts['total_tokens']:,}")

        if additional_context:
            print("   📋 Additional info:")
            for key, value in additional_context.items():
                print(f"      {key}: {value}")

        print(f"   ⏰ Started at: {call_info['start_time']}")
        print(f"   🏁 Completed at: {datetime.now().isoformat()}")
        print("-" * 60)

        self.log_token_usage(
            context={
                "call_name": call_info["call_name"],
                "additional_context": additional_context or {},
            }
        )


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker instance"""
    if not hasattr(get_token_tracker, "_instance"):
        get_token_tracker._instance = TokenTracker()

    return get_token_tracker._instance


def setup_token_tracking() -> TokenCountingHandler:
    """Set up token tracking for the application"""
    tracker = get_token_tracker()
    callback_manager = tracker.setup_callback_manager()

    Settings.callback_manager = callback_manager

    return tracker.token_counter
