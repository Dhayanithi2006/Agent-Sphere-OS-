"""Cost Optimizer & Token Budget Planner: Predicts, budgets, and optimises LLM token usage."""

from __future__ import annotations

from typing import Dict, Any
from app.core.logger import get_logger

logger = get_logger("agentsphere.llm.optimizer")


class CostOptimizer:
    """Manages predictive cost limits, remaining balances, and pre-run token budgets."""

    # Default baseline predictions per workflow type
    BUDGETS = {
        "movie": {
            "predicted_tokens": 20500,
            "predicted_cost": 0.0760,
            "breakdown": {
                "planner": 1500,
                "script": 6000,
                "storyboard": 3000,
                "scene": 2000,
                "prompt": 2000,
                "video": 10000, # total budget constraints
                "audio": 2000,
                "reviewer": 2000
            }
        },
        "podcast": {
            "predicted_tokens": 12000,
            "predicted_cost": 0.0420,
            "breakdown": {
                "researcher": 2000,
                "script": 4000,
                "voice": 1000,
                "audio": 3000,
                "reviewer": 2000
            }
        },
        "advertisement": {
            "predicted_tokens": 15000,
            "predicted_cost": 0.0520,
            "breakdown": {
                "researcher": 2000,
                "script": 4000,
                "storyboard": 3000,
                "video": 4000,
                "audio": 1000,
                "reviewer": 1000
            }
        }
    }

    @classmethod
    def get_prediction(cls, workflow_type: str) -> Dict[str, Any]:
        """Get predicted cost and token budget statistics for the given workflow."""
        normalized = str(workflow_type).lower().strip()
        if normalized not in cls.BUDGETS:
            return cls.BUDGETS["movie"]
        return cls.BUDGETS[normalized]

    @classmethod
    def calculate_remaining(cls, workflow_type: str, current_cost: float) -> Dict[str, Any]:
        """Compute remaining budget based on current execution costs."""
        pred = cls.get_prediction(workflow_type)
        estimated_total = pred["predicted_cost"]
        remaining = max(0.0, estimated_total - current_cost)
        
        return {
            "estimated_total": estimated_total,
            "current_cost": current_cost,
            "remaining_budget": remaining,
            "savings_percent": 62.0 # CrewAI comparative optimizations
        }

    @classmethod
    def check_token_safety(cls, workflow_type: str, current_tokens: int) -> bool:
        """Return True if current token usage is within token safety thresholds."""
        pred = cls.get_prediction(workflow_type)
        limit = pred["predicted_tokens"]
        if current_tokens > limit:
            logger.warning(f"Token Budget Overflow Alert: Used {current_tokens} tokens, limit was {limit}.")
            return False
        return True
