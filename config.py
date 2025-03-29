# config.py

# Basic configuration

DATA_DIR = "data/"

CAMPAIGNS_DIR = DATA_DIR + "campaigns/"

LOGS_DIR = DATA_DIR + "logs/"



# LLM configuration

LLM_PROVIDER = "local"  # Options: "openai", "huggingface", "local", "together", "ollama"

API_KEY = ""

MODEL_NAME = "Beepo-22B"  # Default model name



# Local LLM configuration

LOCAL_MODEL_PATH = "assets/models/airoboros-mistral2.2-7b.Q4_K_S.gguf"  # Path to local GGUF model

LOCAL_MODEL_TYPE = "llama"  # Model architecture type: "llama", "mistral", "falcon", etc.

LOCAL_MODEL_CONTEXT_LENGTH = 4096  # Maximum context length

LOCAL_MODEL_TEMPERATURE = 0.7  # Temperature for generation

LOCAL_MODEL_MAX_TOKENS = 2000  # Maximum tokens to generate



# Free API model configurations

FREE_MODELS = {

    "Llama 3 8B Instruct": {

        "provider": "together",

        "model_id": "meta-llama/Meta-Llama-3-8B-Instruct",

        "description": "Meta's fast & efficient 8B model with excellent response quality (RECOMMENDED)",

        "max_tokens": 1024,

        "temperature": 0.7,

        "system_prompt": "You are a creative and dynamic RPG game master, responding to player actions in a concise and engaging way."

    },

    "Mixtral 8x7B Instruct": {

        "provider": "together",

        "model_id": "mistralai/Mixtral-8x7B-Instruct-v0.1",

        "description": "Powerful mixture-of-experts model with strong reasoning capabilities",

        "max_tokens": 1024,

        "temperature": 0.7

    },

    "Gemma 2 9B Instruct": {

        "provider": "together",

        "model_id": "google/gemma-2-9b-it",

        "description": "Google's efficient open model with good instruction-following capabilities",

        "max_tokens": 1024,

        "temperature": 0.7

    },

    "DeepSeek R1 Distill Llama 70B": {

        "provider": "together",

        "model_id": "deepseek-ai/deepseek-llama-3-r1-70b",

        "description": "Large model with excellent knowledge and reasoning (slowest but highest quality)",

        "max_tokens": 1024,

        "temperature": 0.7

    }

}



# Together API configuration

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"  # Using chat API for better results

TOGETHER_TEMPERATURE = 0.7

TOGETHER_MAX_TOKENS = 1024  # Reduced for faster responses

TOGETHER_CONCURRENCY = 1    # Allow only one API call at a time

TOGETHER_STREAMING = True   # Enable streaming responses



# Ollama configuration (for local API)

OLLAMA_API_URL = "http://localhost:11434/api/generate"



# Vector database configuration

VECTOR_DB_TYPE = "local"  # Use local vector store

VECTOR_DB_URL = "http://localhost"  # Only needed for remote DBs

VECTOR_DB_PORT = 6333  # Default Qdrant port, only needed for remote DBs

VECTOR_DIMENSIONS = 384  # For sentence-transformers

EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Default embedding model



# Memory system configuration

MAX_HISTORY_ITEMS = 20  # Keep testing history manageable

CONTEXT_HISTORY_ITEMS = 5  # Number of recent interactions for context

MEMORY_RELEVANCE_THRESHOLD = 0.7  # Minimum relevance score for memories

CONTRADICTION_THRESHOLD = 0.8  # Threshold for contradiction detection

MAX_CONTEXT_TOKENS = 8000  # Maximum tokens for context



DEFAULT_CAMPAIGN_NAME = "Randal's Adventure"