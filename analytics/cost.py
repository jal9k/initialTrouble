"""OpenAI cost calculator with model pricing."""

from datetime import datetime
from typing import Any


class CostCalculator:
    """Calculate costs for OpenAI API usage."""

    # Pricing per 1M tokens (as of late 2024)
    # Format: model_name -> (input_price_per_1m, output_price_per_1m)
    PRICING: dict[str, tuple[float, float]] = {
        # GPT-4o models
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-2024-11-20": (2.50, 10.00),
        "gpt-4o-2024-08-06": (2.50, 10.00),
        "gpt-4o-2024-05-13": (5.00, 15.00),
        
        # GPT-4o mini
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o-mini-2024-07-18": (0.15, 0.60),
        
        # GPT-4 Turbo
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-4-turbo-2024-04-09": (10.00, 30.00),
        "gpt-4-turbo-preview": (10.00, 30.00),
        "gpt-4-0125-preview": (10.00, 30.00),
        "gpt-4-1106-preview": (10.00, 30.00),
        
        # GPT-4
        "gpt-4": (30.00, 60.00),
        "gpt-4-0613": (30.00, 60.00),
        "gpt-4-0314": (30.00, 60.00),
        
        # GPT-3.5 Turbo
        "gpt-3.5-turbo": (0.50, 1.50),
        "gpt-3.5-turbo-0125": (0.50, 1.50),
        "gpt-3.5-turbo-1106": (1.00, 2.00),
        "gpt-3.5-turbo-instruct": (1.50, 2.00),
        
        # o1 models
        "o1": (15.00, 60.00),
        "o1-2024-12-17": (15.00, 60.00),
        "o1-preview": (15.00, 60.00),
        "o1-preview-2024-09-12": (15.00, 60.00),
        "o1-mini": (3.00, 12.00),
        "o1-mini-2024-09-12": (3.00, 12.00),
    }

    # Default pricing for unknown models (use gpt-4o-mini as baseline)
    DEFAULT_PRICING: tuple[float, float] = (0.15, 0.60)

    def __init__(self):
        """Initialize the cost calculator."""
        self._custom_pricing: dict[str, tuple[float, float]] = {}

    def add_custom_pricing(
        self,
        model_name: str,
        input_price_per_1m: float,
        output_price_per_1m: float,
    ) -> None:
        """Add custom pricing for a model."""
        self._custom_pricing[model_name] = (input_price_per_1m, output_price_per_1m)

    def get_pricing(self, model_name: str) -> tuple[float, float]:
        """Get pricing for a model."""
        # Check custom pricing first
        if model_name in self._custom_pricing:
            return self._custom_pricing[model_name]
        
        # Check built-in pricing
        if model_name in self.PRICING:
            return self.PRICING[model_name]
        
        # Try to match partial model name
        for known_model, pricing in self.PRICING.items():
            if known_model in model_name or model_name in known_model:
                return pricing
        
        # Return default
        return self.DEFAULT_PRICING

    def calculate_cost(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost for a single API call.
        
        Args:
            model_name: The OpenAI model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_price, output_price = self.get_pricing(model_name)
        
        # Convert from per 1M tokens to per token
        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price
        
        return input_cost + output_cost

    def calculate_session_cost(
        self,
        model_name: str,
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ) -> float:
        """Calculate total cost for a session."""
        return self.calculate_cost(model_name, total_prompt_tokens, total_completion_tokens)

    def estimate_monthly_cost(
        self,
        avg_tokens_per_session: int,
        sessions_per_day: int,
        model_name: str = "gpt-4o-mini",
        prompt_ratio: float = 0.7,  # Assume 70% prompt, 30% completion
    ) -> dict[str, float]:
        """Estimate monthly costs based on usage patterns.
        
        Args:
            avg_tokens_per_session: Average total tokens per session
            sessions_per_day: Average number of sessions per day
            model_name: Model to use for pricing
            prompt_ratio: Ratio of prompt tokens to total tokens
            
        Returns:
            Dictionary with cost estimates
        """
        prompt_tokens = int(avg_tokens_per_session * prompt_ratio)
        completion_tokens = avg_tokens_per_session - prompt_tokens
        
        cost_per_session = self.calculate_cost(model_name, prompt_tokens, completion_tokens)
        daily_cost = cost_per_session * sessions_per_day
        monthly_cost = daily_cost * 30
        yearly_cost = daily_cost * 365
        
        return {
            "cost_per_session": cost_per_session,
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
            "tokens_per_session": avg_tokens_per_session,
            "sessions_per_day": sessions_per_day,
            "model": model_name,
        }

    def format_cost(self, cost: float) -> str:
        """Format cost as a readable string."""
        if cost < 0.01:
            return f"${cost:.4f}"
        elif cost < 1.00:
            return f"${cost:.3f}"
        else:
            return f"${cost:.2f}"

    def get_model_tier(self, model_name: str) -> str:
        """Get the pricing tier for a model.
        
        Returns:
            One of: "budget", "standard", "premium", "enterprise"
        """
        input_price, _ = self.get_pricing(model_name)
        
        if input_price <= 0.50:
            return "budget"
        elif input_price <= 5.00:
            return "standard"
        elif input_price <= 15.00:
            return "premium"
        else:
            return "enterprise"

    def compare_models(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        models: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compare costs across different models.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            models: List of models to compare (defaults to popular ones)
            
        Returns:
            List of model comparisons sorted by cost
        """
        if models is None:
            models = [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "o1-mini",
            ]
        
        comparisons = []
        for model in models:
            cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
            input_price, output_price = self.get_pricing(model)
            comparisons.append({
                "model": model,
                "cost": cost,
                "formatted_cost": self.format_cost(cost),
                "tier": self.get_model_tier(model),
                "input_price_per_1m": input_price,
                "output_price_per_1m": output_price,
            })
        
        return sorted(comparisons, key=lambda x: x["cost"])

