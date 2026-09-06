"""Common security models and types."""
from pydantic import BaseModel


class GuardrailResult(BaseModel):
    """Result of guardrail validation."""
    allowed: bool
    reason: str | None = None
