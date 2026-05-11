import os

# All models route through OpenRouter. Temperature and max_tokens are kept
# consistent across families so prompt strategy is the only controlled variable.
MODEL_CONSTANTS = {
    "OPEN_AI": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "openai/gpt-4.1-mini",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        },
    ],
    "GEMINI": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "google/gemini-3-flash-preview",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        }
    ],
    "CLAUDE": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "anthropic/claude-sonnet-4.6",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        }
    ],
    "GEMMA": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "google/gemma-3-27b-it",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        },
    ],
    "LLAMA": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "meta-llama/llama-3.1-8b-instruct",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        },
    ],
    "QWEN": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "qwen/qwen-2.5-72b-instruct",
            "temperature": 0.7,
            "max_tokens": 8192,
            "max_retries": 2,
        },
    ],
    # Uncomment to add Ollama local models in future work.
    # "OLLAMA": [
    #     {
    #         "api_key": os.getenv("OLLAMA_KEY"),
    #         "model": "llama3.2:latest",
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
