"""Google Gemini implementation of BaseAIProvider for Agentic-SRE."""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, Optional

from agentic_sre.ai.base import BaseAIProvider

logger = logging.getLogger("agentic_sre")

# Default model name
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider implementing the Strategy Pattern for crash analysis."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_GEMINI_MODEL) -> None:
        """Initializes GeminiProvider with an API key and model name.

        Args:
            api_key: Optional Gemini API key. Defaults to GEMINI_API_KEY environment variable.
            model_name: Gemini model name. Defaults to 'gemini-3.6-flash'.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazily initializes and caches the Google GenAI client instance."""
        if self._client is None and self.api_key:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _get_fallback_response(self, crash_context: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Generates a fallback structured response under the Fail-Silent rule.

        Args:
            crash_context: Raw sanitized crash metadata.
            reason: Description of why fallback was triggered.

        Returns:
            Fallback dictionary matching required keys.
        """
        failing_comp = (
            f"{crash_context.get('file_name', 'unknown')}:"
            f"{crash_context.get('line_number', 0)} in "
            f"{crash_context.get('function_name', 'unknown')}()"
        )
        return {
            "error_summary": f"Unhandled {crash_context.get('exception_type', 'Exception')}: {crash_context.get('exception_message', '')}",
            "root_cause_hypothesis": f"AI investigation unavailable ({reason}).",
            "failing_component": failing_comp,
            "suggested_fix": "Inspect stack trace and application logs manually.",
        }

    async def analyze_error(self, crash_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes a crash context using the Google Gemini API.

        Args:
            crash_context: Dictionary containing sanitized crash metadata.

        Returns:
            Dict containing error_summary, root_cause_hypothesis, failing_component, and suggested_fix.

        Fail-Silent Guarantee:
            Catches all API or configuration errors, logs them to stderr, and returns a fallback
            dictionary so the host application and background pipeline never crash.
        """
        if not self.api_key:
            logger.warning("[Agentic-SRE] GEMINI_API_KEY environment variable not set. Triggering fail-silent fallback.")
            return self._get_fallback_response(crash_context, "GEMINI_API_KEY not configured")

        try:
            client = self._get_client()
            if client is None:
                return self._get_fallback_response(crash_context, "Failed to initialize Gemini client")

            system_instruction = (
                "You are an expert Senior Site Reliability Engineer (SRE) and Backend Debugging Specialist. "
                "Analyze the provided sanitized application crash context (exception message, stack trace, HTTP request) "
                "and generate a precise, analytical Root Cause Analysis (RCA).\n\n"
                "If historical_context is provided in the crash data, use those past solutions to inform your analysis, "
                "but ensure your final fix applies to the exact line numbers in the current stack trace.\n\n"
                "You MUST respond ONLY with a raw, valid JSON object containing exactly these four keys:\n"
                "- \"error_summary\": A clear 1-2 sentence overview of what went wrong.\n"
                "- \"root_cause_hypothesis\": Deep technical explanation of why the crash occurred based on the code/stack trace.\n"
                "- \"failing_component\": File path, line number, and function name where the failure originated.\n"
                "- \"suggested_fix\": Clean, actionable code change suggestion or diff.\n\n"
                "Do NOT wrap your output in markdown ```json ``` code blocks. Return strictly valid raw JSON without any introductory or concluding text."
            )

            # Intelligently truncate and sanitize historical context items
            raw_historical = crash_context.get("historical_context", [])
            truncated_historical = []
            if isinstance(raw_historical, list):
                for item in raw_historical[:3]:
                    if isinstance(item, dict):
                        clean_item = {
                            "error_summary": str(item.get("error_summary", ""))[:500],
                            "suggested_fix": str(item.get("suggested_fix", ""))[:1000],
                        }
                        truncated_historical.append(clean_item)

            historical_ctx = json.dumps(truncated_historical, indent=2)

            prompt = (
                f"Crash Context:\n"
                f"Exception Type: {crash_context.get('exception_type')}\n"
                f"Exception Message: {crash_context.get('exception_message')}\n"
                f"Failing File: {crash_context.get('file_name')}:{crash_context.get('line_number')} in {crash_context.get('function_name')}()\n"
                f"HTTP Method & URL: {crash_context.get('method')} {crash_context.get('url')}\n"
                f"Sanitized Headers: {json.dumps(crash_context.get('headers', {}))}\n\n"
                f"Historical RAG Context (Past Similar Fixes):\n{historical_ctx}\n\n"
                f"Sanitized Stack Trace:\n{crash_context.get('stack_trace')}\n"
            )

            # Asynchronous API call to Gemini with timeout & transient retry resilience
            max_retries = 2
            response = None
            for attempt in range(max_retries + 1):
                try:
                    response = await asyncio.wait_for(
                        client.aio.interactions.create(
                            model=self.model_name,
                            input=prompt,
                            system_instruction=system_instruction,
                            generation_config={
                                "temperature": 0.1,
                            },
                        ),
                        timeout=15.0,
                    )
                    break
                except (asyncio.TimeoutError, Exception) as req_err:
                    if attempt == max_retries:
                        raise req_err
                    await asyncio.sleep(1.0 * (2 ** attempt))

            raw_text = getattr(response, "output_text", None) or getattr(response, "text", "") or ""

            # Strip any markdown code fences if model returned them despite system prompt
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text, flags=re.IGNORECASE).strip()

            data = json.loads(cleaned_text)

            if not isinstance(data, dict):
                logger.warning(f"[Agentic-SRE] Gemini returned non-dictionary JSON: {type(data)}. Triggering fallback.")
                return self._get_fallback_response(crash_context, "AI output format mismatch")

            # Ensure all required keys exist in dictionary and contain non-empty strings
            required_keys = ["error_summary", "root_cause_hypothesis", "failing_component", "suggested_fix"]
            for key in required_keys:
                if key not in data or not data[key]:
                    data[key] = f"Information not provided by AI for {key}."
                else:
                    data[key] = str(data[key])

            return data

        except Exception as exc:
            # Guarantee Fail-Silent rule: log exception without raising
            logger.error(f"[Agentic-SRE] Gemini Provider API exception: {exc}", exc_info=True)
            return self._get_fallback_response(crash_context, f"API error: {type(exc).__name__}")
