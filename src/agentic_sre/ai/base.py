"""Abstract Base Class for LLM providers in Agentic-SRE."""

import abc
from typing import Any, Dict


class BaseAIProvider(abc.ABC):
    """Abstract Base Class defining the Strategy Interface for AI providers."""

    @abc.abstractmethod
    async def analyze_error(self, crash_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes crash context and returns structured root cause analysis (RCA).

        Args:
            crash_context: Dictionary containing sanitized crash metadata
                (method, url, headers, exception_type, exception_message,
                file_name, line_number, function_name, stack_trace).

        Returns:
            Dict[str, Any] containing the following required keys:
                - error_summary (str): Short 1-2 sentence description of the error.
                - root_cause_hypothesis (str): Deep technical explanation of why it failed.
                - failing_component (str): Exact file, line number, or module affected.
                - suggested_fix (str): Actionable code fix suggestion.
        """
        pass
