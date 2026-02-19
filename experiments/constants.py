import os

MODEL_CONSTANTS = {
    "OPEN_AI": [
        {
            "api_key": os.getenv("OPEN_AI_KEY"),
            "model": "gpt-4.1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_retries": 2,
        },
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "gpt-4.1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_retries": 2,
        }
    ],
    "LLAMA": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "llama-4-maverick",
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_retries": 2,
        }
    ],
    "GEMINI": [
        {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model": "gemini-3-flash-preview",
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_retries": 2,
        }
    ],
    "CLAUDE": [
        {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "claude-sonnet-4.5",
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_retries": 2,
        }
    ],
    "OLLAMA": [{
      "api_key": os.getenv("OLLAMA_KEY"),
        "model": "llama4:latest",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_retries": 2
    }],
}

SCHEMA_CONSTANTS = {"OUTPUT_SCHEMA_V1": {"description": "Output schema version 1"}}

FILE_PATHS = {
    "ANNOTATED_DATA_DIR": "assets/raw/Annotated data",
    "BUSINESS_LOGIC_DIR": "assets/raw/Business Logic",
    "COBOL_PROGRAM_DIR": "assets/raw/COBOL Program",
}


# Pydantic classes
