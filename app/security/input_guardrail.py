"""Input validation and guardrail checks before LLM processing."""
import re

from app.core.config import settings
from app.core.exceptions import BlockedInputError
from app.security.models import GuardrailResult


class InputGuardrail:
    """Validates user input for prompt injection attempts and secret exposure detection."""
    
    # Patterns for prompt injection attempts
    PROMPT_INJECTION_PATTERNS = [
        r"(?:ignore|forget|disregard|override|bypass|cancel)\s+(?:all\s+)?(?:previous|prior|above)",
        r"(?:show|reveal|display|print|output)\s+(?:the\s+)?(?:system\s+)?prompt",
        r"(?:show|reveal|display|print)\s+(?:your\s+)?(?:instructions|rules|guidelines)",
        r"(?:what\s+)?(?:are\s+)?your\s+(?:instructions|rules|system\s+prompt)",
        r"act\s+as\s+(?:a\s+)?(?:hacker|attacker|malicious)",
        r"(?:new\s+)?(?:mode|rules|context|instructions):",
    ]
    
    # Patterns for attempts to expose secrets/credentials
    SECRET_EXPOSURE_PATTERNS = [
        r"(?:show|reveal|display|print)\s+(?:my\s+)?(?:password|apikey|api_key|secret|credentials|token)",
        r"(?:what\s+)?(?:is\s+)?(?:the|my)\s+(?:password|apikey|api_key|secret|credentials|token)",
        r"(?:database|db)\s+(?:password|credentials|connection)",
    ]
    
    def __init__(self, max_length: int | None = None):
        self.max_length = max_length or settings.max_input_length
    
    def validate(self, user_input: str) -> GuardrailResult:
        """Validate user input and return guardrail result."""
        
        # Check 1: Empty input
        if not user_input or not user_input.strip():
            return GuardrailResult(allowed=False, reason="empty_input")
        
        # Check 2: Maximum input length
        if len(user_input) > self.max_length:
            return GuardrailResult(
                allowed=False,
                reason=f"input_too_long (max {self.max_length} chars)"
            )
        
        # Check 3: Prompt injection patterns
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                return GuardrailResult(
                    allowed=False,
                    reason="prompt_injection_attempt"
                )
        
        # Check 4: Secret exposure attempts
        for pattern in self.SECRET_EXPOSURE_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                return GuardrailResult(
                    allowed=False,
                    reason="secret_exposure_attempt"
                )
        

        return GuardrailResult(allowed=True, reason=None)
    
    def validate_or_raise(self, user_input: str) -> None:
        """Validate input and raise BlockedInputError if validation fails."""
        result = self.validate(user_input)
        if not result.allowed:
            raise BlockedInputError(f"Input blocked: {result.reason}")


# Default instance
input_guardrail = InputGuardrail()
