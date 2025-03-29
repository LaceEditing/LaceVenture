# CLAUDE.md - AI Narrative RPG System

## Build & Run Commands
- Run main application: `python main.py`
- Run with specific campaign: `python main.py --campaign <campaign_id>`
- Create new campaign: `python main.py --new <campaign_name> [--setup <setup_file.json>]`
- Run consistency check: `python main.py --campaign <campaign_id> --check`
- Setup local LLM: `python setup_local_llm.py --model <path_to_gguf_file>`

## Test Commands
- Run component tests: `python test_components.py`
- Run system test: `python test_system.py`
- Run single test: `python -c "from test_components import test_vector_store; test_vector_store()"`

## Local LLM Setup
- Install requirements: `pip install -r requirements.txt`
- For local LLM support: `pip install llama-cpp-python`
- For CUDA support: `CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall`
- Configure in config.py: Set `LLM_PROVIDER = "local"` and `LOCAL_MODEL_PATH = "path/to/model.gguf"`

## Code Style Guidelines
- **Imports**: Standard library first, then third-party, then local modules
- **Formatting**: Use 4-space indentation, 79-character line limit
- **Types**: Use type hints from `typing` module for function signatures
- **Naming**: 
  - Classes: CamelCase (`VectorStore`, `CardManager`)
  - Functions/Variables: snake_case (`create_campaign`, `process_turn`)
- **Documentation**: Docstrings for classes and functions ("""triple quotes""")
- **Error Handling**: Use try/except blocks with specific exceptions
- **Logging**: Use the `logging` module instead of print statements for production code