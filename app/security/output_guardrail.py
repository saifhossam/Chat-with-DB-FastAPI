"""Output validation and guardrail checks for LLM responses."""
import re

from app.core.exceptions import InvalidOutputError
from app.security.models import GuardrailResult


class OutputGuardrail:
    """Validates LLM output for empty responses, malformed output, and secret leakage."""
    
    # Patterns that suggest accidental secret/credential leakage
    SECRET_PATTERNS = [
        r"password\s*[:=]\s*['\"]?[\w\-_]+",
        r"(?:api[_-]?)?key\s*[:=]\s*['\"]?[\w\-_]+",
        r"token\s*[:=]\s*['\"]?[\w\-_]+",
        r"(?:secret|credential)\s*[:=]\s*['\"]?[\w\-_]+",
        r"connection[_-]?string\s*[:=]",
        r"(?:db|database)[_-]?(?:password|credential|connection)",
    ]
    
    def validate(self, output: str) -> GuardrailResult:
        """Validate LLM output and return guardrail result."""
        
        # Check 1: Empty or only whitespace output
        if not output or not output.strip():
            return GuardrailResult(allowed=False, reason="empty_output")
        
        # Check 2: Detect obvious secret patterns
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                return GuardrailResult(
                    allowed=False,
                    reason="secret_leakage_detected"
                )
        
        # Check 3: Output is reasonably sized (not excessively long or malformed)
        # Allow up to 100KB of output (reasonable for query results)
        if len(output) > 100_000:
            return GuardrailResult(
                allowed=False,
                reason="output_too_long"
            )
        
        return GuardrailResult(allowed=True, reason=None)
    
    def validate_or_raise(self, output: str) -> None:
        """Validate output and raise InvalidOutputError if validation fails."""
        result = self.validate(output)
        if not result.allowed:
            raise InvalidOutputError(f"Output validation failed: {result.reason}")


# Default instance
output_guardrail = OutputGuardrail()
