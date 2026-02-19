import os
from typing import List
from langchain_openai import ChatOpenAI
from experiments.constants import MODEL_CONSTANTS


class LLM_Factory:

    @staticmethod
    def _getChatOpenAI():
        """
        Return a configured LangChain LLM instance.
        Set OPEN_AI_KEY in the environment (do NOT commit secrets).
        """
        openAiModelList = list()
        openAi_Models = MODEL_CONSTANTS.get("OPEN_AI", [])
        if len(openAi_Models) > 0:
            for modelArgs in openAi_Models:
                if modelArgs["api_key"]:
                    openAiModelList.append(
                        {
                            "ServiceName": "Open AI",
                            "modelArgs": modelArgs,
                            "modelInstance": ChatOpenAI(**modelArgs),
                        }
                    )
        return openAiModelList

    @staticmethod
    def get_AllModels()->List[dict]:
        return [*LLM_Factory._getChatOpenAI()]
