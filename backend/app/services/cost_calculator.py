"""
app/services/cost_calculator.py
===============================
Calculates trace/span costs in USD based on model token counts.
"""

from typing import Dict, Optional

# Pricing per 1,000,000 tokens (USD)
# (input_price_per_1m, output_price_per_1m)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    
    # Google
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}


def calculate_cost(
    model: Optional[str],
    tokens_input: int = 0,
    tokens_output: int = 0,
) -> float:
    """Calculate the estimated USD cost for model token usage.

    Args:
        model: Model identifier (e.g. 'gpt-4o', 'claude-3-5-sonnet')
        tokens_input: Number of prompt / input tokens.
        tokens_output: Number of completion / output tokens.

    Returns:
        Estimated cost in USD rounded to 6 decimal places.
    """
    if not model:
        return 0.0

    model_key = model.lower().strip()
    pricing = MODEL_PRICING.get(model_key)

    # Prefix fallback (e.g. gpt-4o-xxxx -> gpt-4o)
    if not pricing:
        for known_key, rates in MODEL_PRICING.items():
            if model_key.startswith(known_key):
                pricing = rates
                break

    if not pricing:
        return 0.0

    input_cost = (tokens_input / 1_000_000.0) * pricing["input"]
    output_cost = (tokens_output / 1_000_000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)
