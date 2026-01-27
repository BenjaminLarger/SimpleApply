"""
Cost tracking utility for OpenAI API calls.
Tracks token usage and calculates costs based on current OpenAI pricing (2024).
"""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


@dataclass
class APICallCost:
    """Represents the cost of a single API call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime
    operation: str  # job_parsing, skills_matching, project_selection


@dataclass
class CostTracker:
    """Tracks cumulative API costs for a session."""
    calls: List[APICallCost] = field(default_factory=list)

    # Current OpenAI pricing - prices per 1M tokens
    PRICING = {
        "gpt-5": {
            "input": 1.25,    # $1.25 per 1M input tokens
            "output": 10.00   # $10.00 per 1M output tokens
        },
        "gpt-5-nano": {
            "input": 0.05,    # $0.05 per 1M input tokens
            "output": 0.40    # $0.40 per 1M output tokens
        },
        "gpt-5-chat-latest": {
            "input": 1.25,    # $1.25 per 1M input tokens
            "output": 10.00   # $10.00 per 1M output tokens
        },
        "gpt-4.1": {
            "input": 2.00,    # $2.00 per 1M input tokens
            "output": 8.00    # $8.00 per 1M output tokens
        },
        "gpt-4.1-mini": {
            "input": 0.40,    # $0.40 per 1M input tokens
            "output": 1.60    # $1.60 per 1M output tokens
        },
        "gpt-4.1-nano": {
            "input": 0.10,    # $0.10 per 1M input tokens
            "output": 0.40    # $0.40 per 1M output tokens
        },
        "gpt-4o": {
            "input": 2.50,    # $2.50 per 1M input tokens
            "output": 10.00   # $10.00 per 1M output tokens
        }
    }

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost for API call based on token usage.

        Args:
            model: OpenAI model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Normalize model name for pricing lookup
        normalized_model = model.lower()

        # Map model names to pricing keys
        if "gpt-5-chat-latest" in normalized_model:
            pricing_key = "gpt-5-chat-latest"
        elif "gpt-5-nano" in normalized_model:
            pricing_key = "gpt-5-nano"
        elif "gpt-4-mini" in normalized_model:
            pricing_key = "gpt-4-mini"
        elif "gpt-5" in normalized_model:
            pricing_key = "gpt-5"
        elif "gpt-4.1-nano" in normalized_model:
            pricing_key = "gpt-4.1-nano"
        elif "gpt-4.1-mini" in normalized_model:
            pricing_key = "gpt-4.1-mini"
        elif "gpt-4.1" in normalized_model:
            pricing_key = "gpt-4.1"
        elif "gpt-4o" in normalized_model:
            pricing_key = "gpt-4o"
        else:
            # Default to gpt-5-nano pricing for unknown models (most conservative)
            pricing_key = "gpt-5-nano"

        pricing = self.PRICING[pricing_key]

        # Calculate cost: (tokens / 1,000,000) * price_per_million
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def add_call(self, model: str, prompt_tokens: int, completion_tokens: int, operation: str) -> APICallCost:
        """
        Add a new API call to tracking.

        Args:
            model: OpenAI model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            operation: Type of operation (job_parsing, skills_matching, etc.)

        Returns:
            APICallCost object with calculated cost
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        call_cost = APICallCost(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            timestamp=datetime.now(),
            operation=operation
        )

        self.calls.append(call_cost)
        return call_cost

    @property
    def total_cost(self) -> float:
        """Get total cost of all API calls."""
        return sum(call.cost_usd for call in self.calls)

    @property
    def total_tokens(self) -> int:
        """Get total tokens used across all calls."""
        return sum(call.total_tokens for call in self.calls)

    @property
    def total_calls(self) -> int:
        """Get total number of API calls made."""
        return len(self.calls)

    def get_summary(self) -> Dict:
        """
        Get summary statistics of API usage.

        Returns:
            Dictionary with cost and usage statistics
        """
        if not self.calls:
            return {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "total_calls": 0,
                "operations": {},
                "models_used": {}
            }

        # Group by operation
        operations = {}
        for call in self.calls:
            if call.operation not in operations:
                operations[call.operation] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "calls": 0
                }
            operations[call.operation]["cost"] += call.cost_usd
            operations[call.operation]["tokens"] += call.total_tokens
            operations[call.operation]["calls"] += 1

        # Group by model
        models_used = {}
        for call in self.calls:
            if call.model not in models_used:
                models_used[call.model] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "calls": 0
                }
            models_used[call.model]["cost"] += call.cost_usd
            models_used[call.model]["tokens"] += call.total_tokens
            models_used[call.model]["calls"] += 1

        return {
            "total_cost_usd": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "operations": operations,
            "models_used": models_used
        }

    def get_formatted_summary(self) -> str:
        """
        Get a human-readable summary of costs.

        Returns:
            Formatted string with cost information
        """
        summary = self.get_summary()

        if summary["total_calls"] == 0:
            return "No API calls made yet."

        lines = [
            f"💰 Total Cost: ${summary['total_cost_usd']:.4f} USD",
            f"🔢 Total Tokens: {summary['total_tokens']:,}",
            f"📞 Total API Calls: {summary['total_calls']}"
        ]

        if summary["operations"]:
            lines.append("\n📋 By Operation:")
            for op, stats in summary["operations"].items():
                lines.append(f"  • {op}: ${stats['cost']:.4f} ({stats['tokens']:,} tokens, {stats['calls']} calls)")

        if summary["models_used"]:
            lines.append("\n🤖 By Model:")
            for model, stats in summary["models_used"].items():
                lines.append(f"  • {model}: ${stats['cost']:.4f} ({stats['tokens']:,} tokens, {stats['calls']} calls)")

        return "\n".join(lines)


# Global cost tracker instance
_global_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    return _global_tracker


def reset_cost_tracker():
    """Reset the global cost tracker."""
    global _global_tracker
    _global_tracker = CostTracker()


def track_openai_call(response, operation: str) -> APICallCost:
    """
    Track an OpenAI API response and add to global tracker.

    Args:
        response: OpenAI response object
        operation: Type of operation being performed

    Returns:
        APICallCost object with tracked information
    """
    tracker = get_cost_tracker()

    # Extract usage information from response
    usage = response.usage
    model = response.model

    return tracker.add_call(
        model=model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        operation=operation
    )