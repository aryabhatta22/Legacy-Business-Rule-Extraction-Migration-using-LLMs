import json
import time
from typing import Type, Optional, Any, Dict

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from pydantic import BaseModel, ValidationError

from experiments.pipeline_logger import get_logger


class LLMCaller:
    def __init__(self, llm_model, output_schema: Type[BaseModel], task_name: str):
        """Create an LLM caller around a LangChain agent."""
        self.llm_model = llm_model
        self.task_name = task_name
        self.output_schema = output_schema
        self.agent = create_agent(
            model=llm_model,
            tools=[],
            response_format=ProviderStrategy(schema=output_schema),
        )

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove common Markdown code fences before brace extraction.

        LLMs often wrap otherwise valid JSON in ```json fences. Removing the
        fence markers first lets the brace-based extraction stay simple and
        predictable while still handling the most common wrapper.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the JSON object bounded by the first '{' and last '}'.

        This intentionally avoids clever parsing. LLM responses are most often
        recoverable by stripping Markdown fences and then taking the outermost
        braces, which keeps the failure mode easy to debug in experiment logs.
        """
        logger = get_logger()
        logger.info("Starting brace-based JSON extraction", indent=3)

        if not isinstance(text, str) or not text.strip():
            logger.json_extraction(False, "empty text response")
            return None

        cleaned = self._strip_markdown_fences(text)
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")

        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            logger.json_extraction(False, "missing outer JSON braces")
            return None

        json_substring = cleaned[first_brace:last_brace + 1]
        try:
            parsed = json.loads(json_substring)
            logger.json_extraction(True)
            return parsed
        except json.JSONDecodeError as exc:
            logger.json_extraction(False, f"json decode error: {exc.msg}")
            return None

    def _normalize_raw(self, raw: Any) -> Any:
        """Coerce the raw agent output into a schema-parseable Python object."""
        logger = get_logger()
        if isinstance(raw, self.output_schema):
            logger.json_extraction(True, "provider returned schema instance")
            return raw

        if isinstance(raw, dict):
            if "structured_response" in raw:
                logger.json_extraction(True, "provider returned structured_response")
                return raw.get("structured_response")
            logger.json_extraction(True, "provider returned JSON object")
            return raw

        if isinstance(raw, list):
            logger.json_extraction(True, "provider returned JSON list")
            return raw

        if isinstance(raw, str):
            return self._extract_json_from_text(raw) or raw

        return raw

    def call(
        self, prompt: str, max_retries: int = 1, backoff_factor: float = 1.5
    ) -> Dict[str, Any]:
        """Invoke the agent, normalize the response, and validate it."""
        logger = get_logger()
        attempt = 0
        last_raw: Optional[Any] = None
        last_validation_error: Optional[str] = None
        last_exception: Optional[str] = None

        while attempt < max_retries:
            attempt += 1
            try:
                raw_response = self.agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]}
                )
                last_raw = raw_response
                logger.llm_response_received()

                normalized = self._normalize_raw(raw_response)

                if isinstance(normalized, self.output_schema):
                    parsed = normalized
                elif isinstance(normalized, dict):
                    parsed = self.output_schema.model_validate(normalized)
                else:
                    parsed = self.output_schema.model_validate(normalized)

                logger.schema_validation(True)
                return {
                    "success": True,
                    "attempts": attempt,
                    "raw": last_raw,
                    "parsed": parsed,
                    "validation_error": None,
                    "exception": None,
                }

            except ValidationError as exc:
                last_validation_error = exc.json()
                logger.schema_validation(False, "pydantic validation failed")
            except Exception as exc:
                last_exception = str(exc)
                logger.error(
                    f"LLM call failed on attempt {attempt}: {last_exception}",
                    indent=3,
                )

            if attempt < max_retries:
                sleep_for = backoff_factor ** (attempt - 1)
                logger.llm_retry(attempt + 1, max_retries, sleep_for)
                time.sleep(sleep_for)

        logger.error(
            "Exhausted retries for "
            f"{self.task_name}. validation_error={last_validation_error} "
            f"exception={last_exception}",
            indent=3,
        )
        return {
            "success": False,
            "attempts": attempt,
            "raw": last_raw,
            "parsed": None,
            "validation_error": last_validation_error,
            "exception": last_exception,
        }
