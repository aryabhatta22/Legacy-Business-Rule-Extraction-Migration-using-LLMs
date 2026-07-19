import os
from typing import List
from langchain_openrouter import ChatOpenRouter
from experiments.constants import MODEL_CONSTANTS


class LLM_Factory:
    @staticmethod
    def get_AllModels() -> List[dict]:
        # Each key must match an entry in MODEL_CONSTANTS. Families with empty
        # or missing lists are silently skipped by _getOpenRouterModels.
        return [
            *LLM_Factory._getOpenRouterModels("OPEN_AI"),
            *LLM_Factory._getOpenRouterModels("GEMMA"),
            *LLM_Factory._getOpenRouterModels("LLAMA"),
            *LLM_Factory._getOpenRouterModels("QWEN"),
            *LLM_Factory._getOpenRouterModels("OLLAMA"),
        ]

    @staticmethod
    def _getOpenRouterModels(model_family: str):
        """
        Return a configured LangChain ChatOpenRouter instance for each model in the family.
        """
        modelList = []
        models = MODEL_CONSTANTS.get(model_family, [])
        for modelArgs in models:
            api_key = modelArgs.get("api_key") or os.getenv("OPENROUTER_API_KEY")
            model_name = modelArgs.get("model")
            if api_key and model_name:
                modelList.append(
                    {
                        "ServiceName": model_family,
                        "modelArgs": modelArgs,
                        "modelInstance": ChatOpenRouter(
                            api_key=api_key,
                            model=model_name,
                            temperature=modelArgs.get("temperature", 0.7),
                            max_tokens=modelArgs.get("max_tokens", 4096),
                            # A stalled connection without a timeout hangs the
                            # whole pipeline (observed 2026-07-19 on a QWEN call).
                            # 300s: at 120s roughly half of all calls timed out
                            # during a degraded OpenRouter window on 2026-07-19.
                            timeout=modelArgs.get("timeout", 300),
                        ),
                    }
                )
        return modelList
