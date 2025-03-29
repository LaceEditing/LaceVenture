# AI Narrative RPG System

A text-based RPG system with an AI memory system that maintains narrative consistency.

## Features

- Dynamic narrative generation with LLM integration
- Memory system to maintain consistency across game sessions
- Card-based entity management (characters, locations, items, relationships)
- Vector-based memory retrieval for relevant context
- Consistency checking to detect and resolve contradictions
- Supports multiple LLM providers: OpenAI API, Hugging Face, local models

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd AINarrrative

# Easy installation (recommended)
python install_dependencies.py

# Or install dependencies manually
pip install -r requirements.txt
```

The `install_dependencies.py` script will guide you through installing:
- Core dependencies
- Local LLM support (with optional CUDA acceleration)
- Free API model support

## Using AI Language Models

This system supports multiple ways to access AI language models:

1. **Local GGUF Models**: Download and use models directly on your computer
2. **Free API Models**: Access powerful models via internet APIs without downloading
3. **Hybrid Approach**: Switch between local and API models as needed

### Option 1: Local LLM Models

Use downloaded GGUF models (such as Beepo-22B-Q4_K-S.gguf) for offline use.

#### Setup Instructions

1. Install the required dependencies:
   ```bash
   pip install llama-cpp-python
   ```

   With CUDA support (optional, for GPU acceleration):
   ```bash
   CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir
   ```

2. Place your GGUF model files in the `assets/models` directory:
   ```bash
   mkdir -p assets/models
   cp /path/to/your/Beepo-22B-Q4_K-S.gguf assets/models/
   ```

3. Run the setup script to configure your model:
   ```bash
   python setup_local_llm.py
   ```
   
   This will:
   - Check for llama-cpp-python installation
   - List available models in the assets/models directory
   - Let you select a model to use
   - Update config.py automatically

### Option 2: Free API Models

Access powerful models without downloading large files (requires internet).

#### Available Free Models:

- **Llama 3 8B Instruct** (★ Recommended): Meta's latest model with fast response times and high quality
- **Mixtral 8x7B Instruct**: Strong reasoning model with excellent instruction-following
- **Gemma 2 9B Instruct**: Google's efficient open model with good capabilities
- **DeepSeek R1 Distill Llama 70B**: Large model with excellent knowledge (slowest but highest quality)

#### Setup Instructions:

1. Install required dependencies:
   ```bash
   pip install together
   ```

2. View available free models:
   ```bash
   python setup_local_llm.py --show-free
   ```

3. Run the application and select a free model from the menu:
   ```bash
   python main.py
   ```

For best performance with free API models:
- **New**: Responses now stream in real-time for a faster, more interactive experience
- **New**: Llama 3 model provides an excellent balance of speed and quality
- Consider getting a free API key from [Together.ai](https://www.together.ai)
- Be aware of usage limits and potential delays during busy times
- Internet connection is required to use API models

### Running the Application

When you start the application, you'll see a model selection menu:
   - Choose from local models based on size and speed
   - Choose from free API models that don't require downloads
   - Smaller models load faster and generate responses quicker
   - Larger models provide higher quality responses but take longer

### Quick Commands

- **NEW - BLAZING FAST RESPONSES**: 
  - Models now stream responses in real-time for immediate feedback
  - Major performance optimizations to eliminate slowdown during long sessions
  - Background processing for non-critical tasks to keep gameplay smooth
- **NEW - LLAMA 3 ADDED**: Try the recommended Llama 3 model for the best balance of speed and quality 
- **NEW - IMPROVED JSON HANDLING**: More reliable state tracking even during complex gameplay

- List available local models:
  ```bash
  python main.py --list-models
  ```

- Show available free API models:
  ```bash
  python setup_local_llm.py --show-free
  ```

- Run with a specific local model:
  ```bash
  python main.py --model airoboros-mistral2.2-7b.Q4_K_S.gguf
  ```

- Run without the model selection menu:
  ```bash
  python main.py --no-model-menu
  ```

- Setup a specific local model:
  ```bash
  python setup_local_llm.py --model /path/to/model.gguf
  ```

- List models in assets directory:
  ```bash
  python setup_local_llm.py --list
  ```

### Choosing the Right Model

#### Local Models
- **Small models** (< 2GB): Fast loading, quick responses, suitable for simple interactions
- **Medium models** (2-5GB): Good balance of speed and quality
- **Large models** (5-15GB): High quality responses but slower to load and generate
- **Very large models** (> 15GB): Best quality but significantly slower

#### API Models (Internet required)
- **Llama 3 8B Instruct** (★ RECOMMENDED): Fast responses with excellent quality and streaming support
- **Mixtral 8x7B Instruct**: Good for general purpose gameplay and storytelling
- **Gemma 2 9B Instruct**: Fast responses with good quality
- **DeepSeek R1 Distill Llama 70B**: Best quality responses but slower

### Supported Model Formats

- GGUF format models are supported via llama-cpp-python
- Recommended models: Llama 2, Llama 3, Beepo, Mistral, etc.
- Quantized models (Q4, Q5, Q8) are recommended for better performance
- Model recommendations:
  - Beepo-22B-Q4_K-S.gguf (22B parameters, 4-bit quantized)
  - Llama-3-8B-Q4_K_M.gguf (8B parameters, 4-bit quantized)
  - Mistral-7B-v0.1-Q4_K_M.gguf (7B parameters, 4-bit quantized)

## Usage

```bash
# Start the application
python main.py

# Start with a specific campaign
python main.py --campaign <campaign-id>

# Create a new campaign
python main.py --new "My Campaign"

# Run consistency check on a campaign
python main.py --campaign <campaign-id> --check
```

## Development

- Run component tests: `python test_components.py`
- Run system test: `python test_system.py`