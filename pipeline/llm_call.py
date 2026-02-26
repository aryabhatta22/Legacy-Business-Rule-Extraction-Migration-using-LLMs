from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from pydantic import BaseModel, ValidationError
from typing import Type, Optional, Any, Dict
import time
import json
import logging

# schema imports intentionally omitted here; caller provides the output schema type


logger = logging.getLogger(__name__)


class LLMCaller:
    def __init__(self, llm_model, output_schema: Type[BaseModel], task_name: str):
        """Create a simple LLM caller around a LangChain agent.

        The caller keeps a reference to the output Pydantic schema so that
        responses can be validated, raw output captured, and failures retried.
        """
        self.llm_model = llm_model
        self.task_name = task_name
        self.output_schema = output_schema
        self.agent = create_agent(
            model=llm_model,
            tools=[],
            response_format=ProviderStrategy(
                schema=output_schema
            ),  # No tool_message_content needed
        )

    def _normalize_raw(self, raw: Any) -> Any:
        """Try to coerce raw agent output into a Python object for validation.

        - If it's already a dict/list, return as-is.
        - If it's a JSON string, parse it.
        - Otherwise return the original value.
        """
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            # some agents return JSON-like strings; try to parse
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return raw

    def call(
        self, prompt: str, max_retries: int = 3, backoff_factor: float = 1.5
    ) -> Dict[str, Any]:
        """Safely invoke the agent with retries and validation.

        Returns a dict with the following keys:
          - success: bool
          - attempts: int
          - raw: last raw response (or None)
          - parsed: Pydantic model instance when validation succeeds
          - validation_error: validation error text when present
          - exception: exception text when non-validation exceptions occur

        The method will retry on validation failures and on exceptions until
        `max_retries` is reached, using exponential backoff controlled by
        `backoff_factor`.
        """
        attempt = 0
        last_raw: Optional[Any] = None
        last_validation_error: Optional[str] = None
        last_exception: Optional[str] = None

        while attempt < max_retries:
            attempt += 1
            try:
                print(
                    "\t\t\tInvoking agent. Attempt: ",
                    attempt,
                )
                raw_response = self.agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]}
                )
                last_raw = raw_response

                normalized = self._normalize_raw(raw_response)

                # If the normalized output already matches the schema, parse it.
                parsed = None
                try:
                    # If the agent already returned a pydantic model instance, accept it.
                    if isinstance(normalized, self.output_schema):
                        parsed = normalized
                    else:
                        # Attempt to parse/validate using the provided Pydantic schema
                        if isinstance(normalized, (dict, list)):
                            parsed = self.output_schema.model_validate(
                                normalized.get("structured_response")
                            )
                        else:
                            # TODO: fIX If we couldn't coerce into a dict/list, try to pass string as-is
                            parsed = self.output_schema.model_validate(normalized)

                    print(
                        "\t\t\tAgent response validated successfully on attempt: ",
                        attempt,
                    )
                    return {
                        "success": True,
                        "attempts": attempt,
                        "raw": last_raw,
                        "parsed": parsed,
                        "validation_error": None,
                        "exception": None,
                    }

                except ValidationError as ve:
                    # Capture validation errors and retry
                    last_validation_error = ve.json()
                    print(
                        f"\t\t\tValidation failed on attempt: {attempt} with validation error: {last_validation_error}",
                    )

                    # If we've exhausted attempts, break and return failure below
                except Exception as ve2:
                    # Other parsing errors (e.g., when parse_obj throws unexpected types)
                    last_validation_error = str(ve2)
                    print("\t\t\tParsing error on attempt: ", attempt)

            except Exception as exc:
                # Capture any exception raised by agent.invoke itself
                last_exception = str(exc)
                print(
                    f"\t\t\t!!!! agent.invoke() raised an exception on attempt: {attempt} with error: {last_exception}",
                )

            # If we are going to retry, wait with exponential backoff
            if attempt < max_retries:
                sleep_for = backoff_factor ** (attempt - 1)
                print(
                    "Retrying after %.2fs (attempt %d/%d)",
                    sleep_for,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(sleep_for)

        # Exhausted retries - return failure information
        print(
            f"Exhausted {max_retries} attempts for task: {self.task_name}. Last validation_error: {last_validation_error} last_exception: {last_exception}",
        )

        return {
            "success": False,
            "attempts": attempt,
            "raw": last_raw,
            "parsed": None,
            "validation_error": last_validation_error,
            "exception": last_exception,
        }
