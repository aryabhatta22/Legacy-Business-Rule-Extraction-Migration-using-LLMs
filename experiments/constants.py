import os

MODEL_CONSTANTS = {
    "OPEN_AI": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "openai/gpt-4.1-mini",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        },
        # {
        #     "api_key": os.getenv("OPENROUTER_API_KEY"),
        #     "model": "openai/gpt-4o-mini",
        #     "temperature": 0.7,
        #     "max_tokens": 8192,
        #     "max_retries": 2,
        # },
    ],
    # "LLAMA": [
    #     {
    #         "api_key": os.getenv("OPENROUTER_API_KEY"),
    #         "model": "meta-llama/llama-3.1-8b-instruct",
    #         "temperature": 0.7,
    #         "max_tokens": 8192,
    #         "max_retries": 2,
    #     }
    # ],
    # "GEMINI": [
    #     {
    #         "api_key": os.getenv("OPENROUTER_API_KEY"),
    #         "model": "google/gemini-3-flash-preview",
    #         "temperature": 0.7,
    #         "max_tokens": 8192,
    #         "max_retries": 2,
    #     }
    # ],
    # "CLAUDE": [
    #     {
    #         "api_key": os.getenv("OPENROUTER_API_KEY"),
    #         "model": "anthropic/claude-sonnet-4.6",
    #         "temperature": 0.7,
    #         "max_tokens": 8192,
    #         "max_retries": 2,
    #     }
    # ],
    # "OLLAMA": [
    #     {
    #         "api_key": os.getenv("OPENROUTER_API_KEY"),
    #         "model": "llama4:latest",
    #         "temperature": 0.7,
    #         "max_tokens": 8192,
    #         "max_retries": 2,
    #     }
    # ],
}

SCHEMA_CONSTANTS = {"OUTPUT_SCHEMA_V1": {"description": "Output schema version 1"}}

FILE_PATHS = {
    "ANNOTATED_DATA_DIR": "assets/raw/Annotated data",
    "BUSINESS_LOGIC_DIR": "assets/raw/Business Logic",
    "COBOL_PROGRAM_DIR": "assets/raw/COBOL Program",
}
