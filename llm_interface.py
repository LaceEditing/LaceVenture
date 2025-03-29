"""

Interface with language model APIs for text generation and information extraction.

"""



import json

import logging

import time

import random

import os

from typing import Dict, List, Any, Optional, Union

import requests



import openai  # Import is kept for compatibility with existing code

from tenacity import retry, stop_after_attempt, wait_exponential



# Import for local LLM support, with conditional to handle case where it's not installed

try:

    from llama_cpp import Llama

    LOCAL_LLM_AVAILABLE = True

except ImportError:

    LOCAL_LLM_AVAILABLE = False

    logger = logging.getLogger(__name__)

    logger.warning("llama-cpp-python not installed. Local LLM functionality will be limited.")



# Import for Together.ai API

try:

    import together

    TOGETHER_AVAILABLE = True

except ImportError:

    TOGETHER_AVAILABLE = False

    logger = logging.getLogger(__name__)

    logger.warning("Together.ai API client not installed. Together.ai models will not be available.")



# Import for Ollama API (optional)

try:

    import ollama

    OLLAMA_AVAILABLE = True

except ImportError:

    OLLAMA_AVAILABLE = False



from config import (

    API_KEY, MODEL_NAME, LLM_PROVIDER,

    LOCAL_MODEL_PATH, LOCAL_MODEL_TYPE, LOCAL_MODEL_CONTEXT_LENGTH,

    LOCAL_MODEL_TEMPERATURE, LOCAL_MODEL_MAX_TOKENS,

    FREE_MODELS, TOGETHER_API_URL, TOGETHER_TEMPERATURE, TOGETHER_MAX_TOKENS,

    TOGETHER_STREAMING, TOGETHER_CONCURRENCY,

    OLLAMA_API_URL

)



# Set up logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)



class LLMInterface:

    """Interface for communicating with Language Model APIs."""



    def __init__(self, api_key: str = API_KEY, model: str = MODEL_NAME, provider: str = LLM_PROVIDER,

                 model_id: str = None, selected_free_model: str = None):

        """

        Initialize the LLM interface.



        Args:

            api_key: API key for the LLM provider

            model: Model name/version to use

            provider: LLM provider name ("openai", "huggingface", "local", "together", "ollama")

            model_id: Specific model ID for API providers (optional)

            selected_free_model: Name of the selected free model from FREE_MODELS (optional)

        """

        self.api_key = api_key

        self.model = model

        self.provider = provider

        self.model_id = model_id

        self.selected_free_model = selected_free_model



        # If a free model was selected, use its provider and model_id

        if selected_free_model and selected_free_model in FREE_MODELS:

            free_model_config = FREE_MODELS[selected_free_model]

            self.provider = free_model_config["provider"]

            self.model_id = free_model_config["model_id"]

            # Update model_name for logging/display purposes

            self.model = selected_free_model



        self._setup_client()



    def _setup_client(self):

        """Set up the API client based on the provider."""

        if self.provider == "openai":

            # Keep OpenAI setup for compatibility

            pass

        elif self.provider == "huggingface":

            # No setup needed for public inference API

            pass

        elif self.provider == "local":

            # Setup for local models

            self.local_llm = None



            # Check if we can use llama-cpp-python

            if LOCAL_LLM_AVAILABLE:

                try:

                    # Get model path and ensure it exists

                    model_path = LOCAL_MODEL_PATH



                    # If the model path doesn't exist, check if it might be a relative path

                    if not os.path.exists(model_path):

                        # Try to resolve relative to script directory

                        script_dir = os.path.dirname(os.path.abspath(__file__))

                        abs_model_path = os.path.join(script_dir, model_path)



                        if os.path.exists(abs_model_path):

                            model_path = abs_model_path

                            logger.info(f"Found model at: {model_path}")



                    # Verify the model file exists

                    if os.path.exists(model_path):

                        model_name = os.path.basename(model_path)

                        model_size_mb = os.path.getsize(model_path) / (1024 * 1024)



                        # Estimate loading time based on model size

                        if model_size_mb < 2000:

                            estimated_time = "a few seconds"

                        elif model_size_mb < 5000:

                            estimated_time = "about 15-30 seconds"

                        elif model_size_mb < 15000:

                            estimated_time = "1-2 minutes"

                        else:

                            estimated_time = "several minutes"



                        logger.info(f"Loading local model from {model_path}")

                        logger.info(f"Model size: {model_size_mb:.2f} MB")



                        print(f"Loading {model_name} ({model_size_mb:.1f} MB)...")

                        print(f"This may take {estimated_time} depending on your system.")



                        # Record start time to show loading duration

                        start_time = time.time()



                        # Load the model - this might take some time for larger models

                        self.local_llm = Llama(

                            model_path=model_path,

                            n_ctx=LOCAL_MODEL_CONTEXT_LENGTH,

                            verbose=False

                        )



                        # Calculate loading time

                        load_time = time.time() - start_time

                        logger.info(f"Local model {model_name} loaded successfully in {load_time:.2f} seconds")

                        print(f"Model loaded successfully in {load_time:.2f} seconds!")

                    else:

                        logger.warning(f"Local model file not found at {model_path}")

                        logger.warning("Please make sure your model is in the assets/models directory")

                except Exception as e:

                    logger.error(f"Failed to load local model: {e}")

                    self.local_llm = None

            else:

                logger.warning("Local LLM provider selected but llama-cpp-python not installed")

                logger.info("Install with: pip install llama-cpp-python")



        elif self.provider == "together":

            # Setup for Together.ai API

            if TOGETHER_AVAILABLE:

                # Set API key for Together client

                if not self.api_key or self.api_key == "your_api_key_here" or self.api_key == "":

                    logger.warning("No Together.ai API key provided, will use guest access")

                    logger.warning("Guest access has limited quota and may be slow or unavailable")

                    # Explicitly set to empty to use guest access

                    together.api_key = ""

                else:

                    together.api_key = self.api_key

                    logger.info(f"Together.ai API client initialized with model: {self.model_id}")



                # Log information about the model being used

                print(f"Using Together.ai API with model: {self.model_id}")

                print("This is a free API service with quotas - response times may vary.")

            else:

                logger.error("Together.ai provider selected but 'together' package not installed")

                logger.info("Install with: pip install together")

                print("Error: Together.ai package not installed. Please install it with:")

                print("  pip install together")



        elif self.provider == "ollama":

            # Setup for Ollama API (local API server)

            if OLLAMA_AVAILABLE:

                logger.info(f"Using Ollama with model: {self.model_id or self.model}")

                print(f"Using Ollama local API with model: {self.model_id or self.model}")

                print("Ensure Ollama is running with the selected model loaded.")

            else:

                logger.error("Ollama provider selected but 'ollama' package not installed")

                logger.info("Install with: pip install ollama")

                print("Error: Ollama package not installed. Please install it with:")

                print("  pip install ollama")



    def _create_prompt(self, user_input: str, context: str) -> str:

        """Create a standard prompt for LLMs that encourages concise responses."""

        # Check if context is already minimalist (coming from optimized memory system)

        if context.count('#') <= 5 and "INSTRUCTIONS" in context and len(context) < 1000:

            # Context is already optimized, use it directly

            if "PLAYER:" in context and "GAME MASTER:" not in context:

                # Format is already correct

                return context

            else:

                # Add the standard format

                return f"{context}\n\nPLAYER: {user_input}\n\nGAME MASTER:"



        # Otherwise, extract relevant context (lightweight version for speed)

        relevant_context = self._extract_relevant_context(context, user_input)



        # Ultra-optimized prompt focused on speed

        return f"""You are a dynamic RPG game master. Be concise and direct.

Keep responses under 3 sentences for a fast gameplay experience.



CONTEXT:

{relevant_context}



PLAYER: {user_input}



GAME MASTER:"""



    def _generate_with_together_api(self, prompt: str) -> str:

        """Generate text using Together.ai API with streaming for faster perceived response."""

        # Check if we have model-specific configuration

        model_config = None

        for model_name, config in FREE_MODELS.items():

            if config.get("model_id") == self.model_id:

                model_config = config

                break



        # Get model-specific settings or use defaults

        max_tokens = model_config.get("max_tokens", TOGETHER_MAX_TOKENS)

        temperature = model_config.get("temperature", TOGETHER_TEMPERATURE)

        system_prompt = model_config.get("system_prompt", "You are a creative RPG game master.")



        # ULTRA-FAST OPTIMIZATION - Shorten system prompt to bare minimum

        fast_system_prompt = "You are an RPG game master. Be concise and direct."



        # Start timing

        start_time = time.time()



        try:

            # Check if Together API is configured

            if not hasattr(together, 'api_key'):

                together.api_key = ""  # Use guest access



            # Use even faster temperature for first tokens (ensures quick start)

            # Lower temperature makes the model more decisive for faster responses

            fast_temp = max(0.1, temperature - 0.3)



            # Create the messages - keep it minimal

            messages = [

                {"role": "system", "content": fast_system_prompt},

                {"role": "user", "content": prompt}

            ]



            # Always use streaming for better UX

            try:

                # Initialize streaming

                stream = together.ChatCompletions.create(

                    model=self.model_id,

                    messages=messages,

                    max_tokens=max_tokens,

                    temperature=fast_temp,  # Lower temp for faster first tokens

                    top_p=0.1,  # Lower top_p for more decisive, faster first tokens

                    repetition_penalty=1.0,  # No repetition penalty to avoid computations

                    stop=["PLAYER:", "\nPLAYER:"],

                    stream=True,

                )



                # Stream the response for immediate feedback

                # Print the first token ASAP to reduce perceived latency

                generated_text = ""

                printed_first_token = False



                # Process the stream in chunks

                for chunk in stream:

                    if chunk.choices and chunk.choices[0].delta.content:

                        content = chunk.choices[0].delta.content



                        # Print content

                        if not printed_first_token:

                            # First token gets special treatment - print immediately with flush

                            print(content, end="", flush=True)

                            printed_first_token = True

                        else:

                            # Rest of tokens

                            print(content, end="", flush=True)



                        # Accumulate text

                        generated_text += content



                # Finish with newline

                print()



            except Exception as stream_error:

                # Fall back to non-streaming if streaming fails

                logger.warning(f"Streaming failed: {stream_error}, falling back to regular API")



                print("Generating response... ", end="", flush=True)



                # Fall back to non-streaming API

                response = together.ChatCompletions.create(

                    model=self.model_id,

                    messages=messages,

                    max_tokens=max_tokens,

                    temperature=temperature,

                    stop=["PLAYER:", "\nPLAYER:"],

                )



                # Extract and print the text

                generated_text = response.choices[0].message.content.strip()

                print("\r" + generated_text)



            # Clean up the response if needed

            if "GAME MASTER:" in generated_text:

                generated_text = generated_text.split("GAME MASTER:")[-1].strip()



            # Log the generation time

            generation_time = time.time() - start_time

            logger.info(f"Response generated in {generation_time:.2f} seconds")



            return generated_text



        except ImportError:

            logger.error("The 'together' package is not installed")

            print("\rError: Together package not installed")

            return "I'm having trouble connecting to the language model. Please try a local model instead."



        except Exception as e:

            logger.error(f"Together.ai API error: {e}")

            print(f"\rI encountered an error generating a response.")



            # For auth issues, give simple guidance

            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():

                return "I'm having trouble with API authentication. You can try selecting a different model or restart the game to enter an API key."

            else:

                return "I'm having trouble connecting to the language model. Please try again with a simpler action."



    def _generate_with_ollama(self, prompt: str) -> str:

        """Generate text using Ollama local API."""

        logger.info(f"Generating response with Ollama using model: {self.model_id or self.model}")

        print("Generating response via Ollama...", end="", flush=True)



        # Record start time for generation

        start_time = time.time()



        try:

            # Use the Ollama client library

            response = ollama.generate(

                model=self.model_id or self.model,

                prompt=prompt,

                options={

                    "temperature": LOCAL_MODEL_TEMPERATURE,

                    "num_predict": LOCAL_MODEL_MAX_TOKENS,

                    "stop": ["PLAYER:", "\nPLAYER:"]

                }

            )



            # Calculate generation time

            generation_time = time.time() - start_time



            # Extract the generated text

            generated_text = response["response"].strip()



            # Clean up the response if needed

            if "GAME MASTER:" in generated_text:

                generated_text = generated_text.split("GAME MASTER:")[-1].strip()



            logger.info(f"Ollama generated a response in {generation_time:.2f} seconds")

            print(f"\rResponse generated in {generation_time:.2f} seconds.        ")



            return generated_text



        except Exception as e:

            logger.error(f"Ollama API error: {e}")

            print(f"\rOllama API error: {e}                                      ")

            return None



    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))

    def generate_response(self, user_input: str, context: str) -> str:

        """

        Generate a response from the LLM based on user input and context.



        Args:

            user_input: The user's text input

            context: The context to provide to the LLM



        Returns:

            The LLM's generated response

        """

        # Create a standard prompt

        prompt = self._create_prompt(user_input, context)



        # Route to the appropriate provider

        if self.provider == "local" and self.local_llm is not None:

            try:

                # Generate response from local model

                logger.info("Generating response with local LLM")

                print("⏳ Generating... ", end="", flush=True)



                # Record start time for generation

                start_time = time.time()



                # Optimize for first response vs subsequent responses

                is_first_response = "Game is starting" in prompt or len(prompt) < 500



                # Use faster generation parameters for first response

                temp = 0.1 if is_first_response else LOCAL_MODEL_TEMPERATURE

                tokens = min(512, LOCAL_MODEL_MAX_TOKENS) if is_first_response else LOCAL_MODEL_MAX_TOKENS



                try:

                    # Check if streaming is supported (newer llama-cpp-python versions)

                    if hasattr(self.local_llm, 'create_completion') and callable(getattr(self.local_llm, 'create_completion')):

                        print("\r", end="")  # Clear the waiting message



                        # Collect the generated text

                        generated_text = ""

                        printed_first_token = False



                        # Use streaming API with optimized parameters

                        for chunk in self.local_llm.create_completion(

                            prompt,

                            max_tokens=tokens,

                            temperature=temp,

                            stop=["PLAYER:", "\nPLAYER:"],

                            stream=True,

                            # Add more params to speed up first token generation

                            repeat_penalty=1.0,  # Disable repeat penalty for first response

                            top_k=10 if is_first_response else 40,  # Narrow beam for faster first tokens

                            top_p=0.1 if is_first_response else 0.9  # More decisive first tokens

                        ):

                            if "choices" in chunk and chunk["choices"] and "text" in chunk["choices"][0]:

                                text = chunk["choices"][0]["text"]



                                # Special handling for first token - print ASAP

                                if not printed_first_token:

                                    print(text, end="", flush=True)

                                    printed_first_token = True

                                else:

                                    print(text, end="", flush=True)



                                generated_text += text



                        # Add a newline after streaming completes

                        print()

                    else:

                        # Fall back to non-streaming for older versions, with optimized parameters

                        response = self.local_llm(

                            prompt,

                            max_tokens=tokens,

                            temperature=temp,

                            stop=["PLAYER:", "\nPLAYER:"],

                            repeat_penalty=1.0,

                            top_k=10 if is_first_response else 40,

                            top_p=0.1 if is_first_response else 0.9

                        )



                        # Extract the generated text

                        generated_text = response["choices"][0]["text"].strip()



                        # Print the response

                        print("\r" + generated_text)

                except Exception as e:

                    # If streaming fails, use ultra-lightweight generation with minimal parameters

                    logger.warning(f"Streaming not supported or failed: {e}")

                    response = self.local_llm(

                        prompt,

                        max_tokens=tokens,

                        temperature=temp,

                        stop=["PLAYER:", "\nPLAYER:"],

                    )



                    # Extract the generated text

                    generated_text = response["choices"][0]["text"].strip()



                    # Print the response

                    print("\r" + generated_text)



                # Calculate generation time

                generation_time = time.time() - start_time



                # Clean up the response if needed

                if "GAME MASTER:" in generated_text:

                    generated_text = generated_text.split("GAME MASTER:")[-1].strip()



                logger.info(f"Local LLM generated a response in {generation_time:.2f} seconds")



                return generated_text

            except Exception as e:

                logger.error(f"Local LLM error: {e}")

                logger.info("Falling back to other methods")

                # Continue to fallbacks



        elif self.provider == "together" and TOGETHER_AVAILABLE:

            # Use Together.ai API

            generated_text = self._generate_with_together_api(prompt)

            if generated_text:

                return generated_text

            # Continue to fallbacks if Together.ai fails



        elif self.provider == "ollama" and OLLAMA_AVAILABLE:

            # Use Ollama API

            generated_text = self._generate_with_ollama(prompt)

            if generated_text:

                return generated_text

            # Continue to fallbacks if Ollama fails



        # Try OpenAI if API key is provided (for backward compatibility)

        if self.api_key and self.api_key != "your_api_key_here":

            try:

                # Try to use OpenAI with new client format

                try:

                    client = openai.OpenAI(api_key=self.api_key)

                    response = client.chat.completions.create(

                        model=self.model,

                        messages=[

                            {"role": "system", "content": "You are a dynamic RPG game master. Maintain consistency with the provided context."},

                            {"role": "system", "content": f"CONTEXT:\n{context}"},

                            {"role": "user", "content": user_input}

                        ],

                        max_tokens=2000,

                        temperature=0.7

                    )

                    return response.choices[0].message.content

                except Exception as e:

                    logger.error(f"New OpenAI client failed: {e}")

                    # Try legacy format as fallback

                    response = openai.ChatCompletion.create(

                        model=self.model,

                        messages=[

                            {"role": "system", "content": "You are a dynamic RPG game master."},

                            {"role": "system", "content": f"CONTEXT:\n{context}"},

                            {"role": "user", "content": user_input}

                        ],

                        max_tokens=2000,

                        temperature=0.7

                    )

                    return response.choices[0].message.content

            except Exception as e:

                logger.error(f"OpenAI API error: {e}")

                # Continue to fallback



        # HuggingFace Inference API

        try:

            response = self.try_huggingface_inference(user_input, context)

            if response:

                return response

        except Exception as e:

            logger.error(f"HuggingFace error: {e}")



        # Ultimate fallback - rule-based

        return self.generate_rule_based_response(user_input, context)



    def try_huggingface_inference(self, user_input: str, context: str) -> str:

        """

        Try to use HuggingFace's public inference API.



        Args:

            user_input: The user's text input

            context: The context to provide to the LLM



        Returns:

            Generated response or None if failed

        """

        # List of free models to try

        models = [

            "google/flan-t5-small",

            "facebook/blenderbot-400M-distill",

            "EleutherAI/gpt-neo-125m"

        ]



        # Extract relevant context (to keep prompt short)

        relevant_context = self._extract_relevant_context(context, user_input)



        # Try each model until one works

        for model in models:

            try:

                url = f"https://api-inference.huggingface.co/models/{model}"



                prompt = f"""

                You are a game master for an RPG game. Be creative and engaging.

                

                CONTEXT:

                {relevant_context}

                

                PLAYER: {user_input}

                

                GAME MASTER:

                """



                headers = {}

                if self.api_key and self.api_key != "your_api_key_here":

                    headers["Authorization"] = f"Bearer {self.api_key}"



                response = requests.post(

                    url,

                    json={"inputs": prompt, "parameters": {"max_length": 150}},

                    headers=headers,

                    timeout=10

                )



                if response.status_code == 200:

                    result = response.json()

                    if isinstance(result, list):

                        return result[0]["generated_text"].split("GAME MASTER:")[-1].strip()

                    else:

                        return result["generated_text"].split("GAME MASTER:")[-1].strip()

                else:

                    logger.warning(f"HuggingFace API returned status {response.status_code} for model {model}")

                    continue

            except Exception as e:

                logger.warning(f"Error with model {model}: {e}")

                continue



        # If all models failed, return None to trigger fallback

        return None



    def _extract_relevant_context(self, context: str, user_input: str) -> str:

        """Extract only the most relevant parts of context to keep prompts short for faster responses."""

        # Split context into sections

        sections = context.split("#")



        # Priority keywords for context relevance

        high_priority_keys = ["current location", "characters present", "current situation", "player status"]

        medium_priority_keys = ["recent events", "quest", "mission", "objective", "inventory"]



        # Organize sections by priority

        high_priority_sections = []

        medium_priority_sections = []

        low_priority_sections = []



        for section in sections:

            if any(key in section.lower() for key in high_priority_keys):

                high_priority_sections.append("#" + section)

            elif any(key in section.lower() for key in medium_priority_keys):

                medium_priority_sections.append("#" + section)

            else:

                low_priority_sections.append("#" + section)



        # For most models, we want to keep context compact for faster responses

        # Include high priority sections first, then add medium priority if needed

        relevant_parts = high_priority_sections



        # Add medium priority sections if we have few high priority ones

        if len(relevant_parts) < 3:

            relevant_parts.extend(medium_priority_sections[:2])  # Add up to 2 medium priority sections



        # If we have too little context, add a limited number of low priority sections

        if len(relevant_parts) < 2:

            relevant_parts.extend(low_priority_sections[:1])  # Add just 1 low priority section



        # If we have relevant parts, join them

        if relevant_parts:

            return "\n".join(relevant_parts)

        else:

            # If no relevant parts were found, take only first few and last few lines

            lines = context.split("\n")

            if len(lines) > 15:  # Reduced from 20 to 15 for faster processing

                return "\n".join(lines[:5] + ["..."] + lines[-5:])  # Reduced from 10 to 5

            return context



    def _generate_with_together_api(self, prompt: str) -> str:

        """Generate text using Together.ai API with streaming for faster perceived response."""

        # Check if we have model-specific configuration

        model_config = None

        for model_name, config in FREE_MODELS.items():

            if config.get("model_id") == self.model_id:

                model_config = config

                break



        # Get model-specific settings or use defaults

        max_tokens = model_config.get("max_tokens", TOGETHER_MAX_TOKENS)

        temperature = model_config.get("temperature", TOGETHER_TEMPERATURE)

        system_prompt = model_config.get("system_prompt", "You are a creative RPG game master.")



        # ULTRA-FAST OPTIMIZATION - Shorten system prompt to bare minimum

        fast_system_prompt = "You are an RPG game master. Be concise and direct."



        # Start timing

        start_time = time.time()



        try:

            # Check if Together API is configured

            if not hasattr(together, 'api_key'):

                together.api_key = ""  # Use guest access



            # Lower temperature makes the model more decisive for faster responses

            fast_temp = max(0.1, temperature - 0.3)



            # Try to use the together API client based on what's available

            try:

                # First try the modern Together API (v2+)

                if hasattr(together, 'ChatCompletions'):

                    # Create the messages - keep it minimal

                    messages = [

                        {"role": "system", "content": fast_system_prompt},

                        {"role": "user", "content": prompt}

                    ]



                    # Always use streaming for better UX

                    try:

                        # Initialize streaming

                        stream = together.ChatCompletions.create(

                            model=self.model_id,

                            messages=messages,

                            max_tokens=max_tokens,

                            temperature=fast_temp,

                            top_p=0.1,

                            repetition_penalty=1.0,

                            stop=["PLAYER:", "\nPLAYER:"],

                            stream=True,

                        )



                        # Stream the response for immediate feedback

                        # Print the first token ASAP to reduce perceived latency

                        generated_text = ""

                        printed_first_token = False



                        # Process the stream in chunks

                        for chunk in stream:

                            if chunk.choices and chunk.choices[0].delta.content:

                                content = chunk.choices[0].delta.content



                                # Print content

                                if not printed_first_token:

                                    # First token gets special treatment - print immediately with flush

                                    print(content, end="", flush=True)

                                    printed_first_token = True

                                else:

                                    # Rest of tokens

                                    print(content, end="", flush=True)



                                # Accumulate text

                                generated_text += content



                        # Finish with newline

                        print()



                    except Exception as stream_error:

                        # Fall back to non-streaming

                        logger.warning(f"Streaming failed: {stream_error}, falling back to regular API")

                        print("Generating response... ", end="", flush=True)



                        # Fall back to non-streaming API

                        response = together.ChatCompletions.create(

                            model=self.model_id,

                            messages=messages,

                            max_tokens=max_tokens,

                            temperature=temperature,

                            stop=["PLAYER:", "\nPLAYER:"],

                        )



                        # Extract and print the text

                        generated_text = response.choices[0].message.content.strip()

                        print("\r" + generated_text)



                # Try fallback to older Together API version

                elif hasattr(together, 'complete'):

                    # Use older complete API

                    print("Using older Together API...")

                    response = together.complete(

                        prompt=f"{fast_system_prompt}\n\n{prompt}",

                        model=self.model_id,

                        max_tokens=max_tokens,

                        temperature=fast_temp,

                        stop=["PLAYER:", "\nPLAYER:"],

                    )

                    generated_text = response['output']['choices'][0]['text'].strip()



                # Try direct API call as last resort

                else:

                    logger.warning("Using direct API call to Together.ai")



                    # Build request for direct API call

                    headers = {

                        "Authorization": f"Bearer {together.api_key}" if hasattr(together,

                                                                                 'api_key') and together.api_key else ""

                    }

                    payload = {

                        "model": self.model_id,

                        "prompt": f"{fast_system_prompt}\n\n{prompt}\n\nAI Game Master:",

                        "max_tokens": max_tokens,

                        "temperature": fast_temp,

                        "stop": ["PLAYER:", "\nPLAYER:"]

                    }



                    # Make API request

                    response = requests.post(

                        "https://api.together.xyz/v1/completions",

                        headers=headers,

                        json=payload

                    )



                    if response.status_code == 200:

                        response_json = response.json()

                        generated_text = response_json["choices"][0]["text"].strip()

                    else:

                        raise Exception(f"API request failed with status {response.status_code}: {response.text}")



            except Exception as api_error:

                logger.error(f"Together.ai API error: {api_error}")

                # Try one more fallback to direct API call

                return f"I encountered an error generating a response. Please try again with a simpler action."



            # Clean up the response if needed

            if "GAME MASTER:" in generated_text:

                generated_text = generated_text.split("GAME MASTER:")[-1].strip()



            # Log the generation time

            generation_time = time.time() - start_time

            logger.info(f"Response generated in {generation_time:.2f} seconds")



            return generated_text



        except Exception as e:

            logger.error(f"Together.ai API error: {e}")

            print(f"\rI encountered an error generating a response.")



            # For auth issues, give simple guidance

            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():

                return "I'm having trouble with API authentication. You can try selecting a different model or restart the game to enter an API key."

            else:

                return "I'm having trouble connecting to the language model. Please try again with a simpler action."



    def generate_rule_based_response(self, user_input: str, context: str) -> str:

        """Generate a rule-based response for testing when no LLM is available."""

        user_input_lower = user_input.lower()



        # Extract location from context

        current_location = "unknown location"

        for line in context.split('\n'):

            if "CURRENT LOCATION:" in line:

                current_location = line.split("CURRENT LOCATION:")[-1].strip()

                break



        # Check for common commands

        if "look" in user_input_lower or "examine" in user_input_lower:

            return f"You look around {current_location}. You see various details that catch your attention."



        if "go" in user_input_lower or "move" in user_input_lower:

            direction = next((d for d in ["north", "south", "east", "west"] if d in user_input_lower), "forward")

            return f"You move {direction}, exploring the area around you."



        if "talk" in user_input_lower or "speak" in user_input_lower:

            if "wizard" in user_input_lower or "old" in user_input_lower:

                return "The Old Wizard strokes his beard thoughtfully. 'What brings you to our village, traveler?'"

            return "You speak, but nobody seems to be listening."



        if "take" in user_input_lower or "pick up" in user_input_lower:

            if "scroll" in user_input_lower or "magic scroll" in user_input_lower:

                return "You carefully pick up the Magic Scroll. The runes glow faintly as you touch it."

            return "You don't see anything you can take."



        # Default response

        return f"You consider your options in {current_location}. What would you like to do next?"



    def _generate_look_response(self, user_input: str, location: str, characters: List[str], items: List[str]) -> str:

        """Generate a response for look/examine commands."""

        # Check if looking at something specific

        specific_targets = [

            term for term in user_input.split()

            if term not in ["look", "at", "examine", "check", "see", "the", "around"]

        ]



        if specific_targets:

            target = specific_targets[0]



            # Check if looking at a character

            for character in characters:

                if target in character.lower():

                    return f"You observe {character}. They seem to be going about their business in {location}."



            # Check if looking at an item

            for item in items:

                if target in item.lower():

                    return f"You examine the {item}. It looks interesting and potentially useful."



            # Generic object response

            return f"You look at the {target}, but don't notice anything particularly special about it."



        # General look around response

        response = f"You look around {location}."



        if characters:

            if len(characters) == 1:

                response += f" You see {characters[0]}."

            else:

                response += f" You see several people: {', '.join(characters[:-1])} and {characters[-1]}."



        if items:

            if len(items) == 1:

                response += f" There is a {items[0]} here."

            else:

                response += f" There are several items of interest: {', '.join(items[:-1])} and {items[-1]}."



        return response



    def _generate_movement_response(self, user_input: str, location: str) -> str:

        """Generate a response for movement commands."""

        directions = ["north", "south", "east", "west", "up", "down", "left", "right", "forward", "backward"]



        # Check if a specific direction was mentioned

        for direction in directions:

            if direction in user_input:

                return f"You move {direction} from {location}. The path continues ahead."



        return f"You move forward from {location}, exploring the area around you."



    def _generate_talk_response(self, user_input: str, characters: List[str]) -> str:

        """Generate a response for conversation commands."""

        if not characters:

            return "There's no one here to talk to."



        # Check if talking to a specific character

        for character in characters:

            if character.lower() in user_input:

                return f"{character} listens to what you have to say and nods thoughtfully."



        # Default to first character if none specified

        return f"You speak with {characters[0]}. They seem interested in what you have to say."



    def _generate_take_response(self, user_input: str, items: List[str]) -> str:

        """Generate a response for take/grab commands."""

        if not items:

            return "There's nothing obvious here to take."



        # Check if taking a specific item

        for item in items:

            if item.lower() in user_input:

                return f"You take the {item} and add it to your inventory."



        # Default if no specific item mentioned

        return "You need to specify what you want to take."



    def _generate_combat_response(self, user_input: str, characters: List[str]) -> str:

        """Generate a response for combat commands."""

        if not characters:

            return "There's no one here to fight."



        # Check if attacking a specific character

        for character in characters:

            if character.lower() in user_input:

                return f"You ready your weapon and prepare to attack {character}. They look alarmed and defensive."



        # Default to first character if none specified

        return f"You take an aggressive stance. {characters[0]} seems startled by your hostile behavior."



    def _generate_use_response(self, user_input: str, items: List[str]) -> str:

        """Generate a response for use commands."""

        # Generic use response

        return "You attempt to use that, but nothing obvious happens."



    def _generate_generic_response(self, location: str) -> str:

        """Generate a generic response when no specific command is recognized."""

        generic_responses = [

            f"You consider your options carefully in {location}.",

            f"The atmosphere in {location} feels charged with possibility.",

            f"You take a moment to gather your thoughts in {location}.",

            f"You wait patiently, observing your surroundings in {location}.",

            f"Time passes slowly in {location} as you contemplate your next move."

        ]

        return random.choice(generic_responses) + " What will you do next?"



    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))

    def extract_structured_data(self, prompt: str) -> Dict[str, Any]:

        """

        Extract structured data using the LLM.



        Args:

            prompt: The extraction prompt



        Returns:

            Structured data in dictionary format

        """

        # Try Together.ai API first if that's the current provider

        if self.provider == "together" and TOGETHER_AVAILABLE:

            try:

                # Create a system prompt for more reliable JSON extraction

                system_prompt = """

                You are a JSON extraction expert. Extract structured information as JSON from the user's text.

                IMPORTANT: Follow these rules exactly:

                1. Respond ONLY with valid JSON - no explanations or other text

                2. Use the exact keys and structure requested by the user 

                3. If you can't extract certain information, use empty arrays or null values

                4. Ensure all JSON syntax is correct - properly escaped quotes, no trailing commas, etc.

                5. Do not add any prefix or suffix to your JSON response

                """



                # Create the messages for the extraction

                messages = [

                    {"role": "system", "content": system_prompt},

                    {"role": "user", "content": prompt + "\n\nOutput the extracted information as valid JSON only."}

                ]



                logger.info("Extracting structured data with Together.ai API")

                print("Processing game state... ", end="", flush=True)



                # Use the Together API for extraction

                response = together.ChatCompletions.create(

                    model=self.model_id,

                    messages=messages,

                    max_tokens=1024,

                    temperature=0.1,  # Very low temperature for deterministic JSON output

                )



                # Get the generated text

                response_text = response.choices[0].message.content.strip()



                # Try to parse the JSON

                try:

                    # Handle case where LLM might wrap response in code blocks

                    if "```json" in response_text:

                        json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()

                    elif "```" in response_text:

                        json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()

                    else:

                        json_str = response_text



                    # Parse the JSON

                    result = json.loads(json_str)

                    print("\rGame state updated.                  ")

                    return result

                except json.JSONDecodeError as e:

                    logger.warning(f"Together.ai API returned invalid JSON: {str(e)}")

                    # Return a default structure with the raw extraction

                    print("\rWarning: Could not parse game state properly. Continuing with limited updates.")

                    return {

                        "character_changes": [],

                        "location_changes": [],

                        "item_changes": [],

                        "relationship_changes": [],

                        "story_developments": [],

                        "current_focus": {

                            "characters": [],

                            "location": None,

                            "items": []

                        },

                        "raw_extraction": response_text

                    }

            except Exception as e:

                logger.error(f"Together.ai extraction error: {e}")

                print(f"\rError processing game state: {e}")

                # Continue to fallbacks



        # Try local LLM if available and provider is set to "local"

        if self.provider == "local" and self.local_llm is not None:

            try:

                structured_prompt = f"""

                You are a precise data extraction assistant. Extract structured information from this text.

                Return valid JSON format only. Focus on extracting entities, relationships, and key information.



                {prompt}



                JSON output:

                ```json

                """



                logger.info("Extracting structured data with local LLM")

                response = self.local_llm(

                    structured_prompt,

                    max_tokens=LOCAL_MODEL_MAX_TOKENS,

                    temperature=0.2,  # Lower temperature for more deterministic output

                )



                # Extract the generated text

                response_text = response["choices"][0]["text"].strip()



                # Try to parse the response as JSON

                try:

                    # Add closing JSON block format if needed

                    if not response_text.endswith("}"):

                        response_text += "\n}"



                    # If response starts with backticks, remove them

                    if "```" in response_text:

                        json_str = response_text.split("```", 1)[1].split("```", 1)[0]

                        return json.loads(json_str)

                    else:

                        return json.loads(response_text)

                except json.JSONDecodeError:

                    logger.warning("Failed to parse local LLM output as JSON")

                    # Return raw text instead

                    return {"raw_extraction": response_text}

            except Exception as e:

                logger.error(f"Local LLM extraction error: {e}")

                # Continue to fallbacks



        # Try OpenAI if configured

        if self.api_key and self.api_key != "your_api_key_here":

            try:

                # Try the new client format first

                try:

                    client = openai.OpenAI(api_key=self.api_key)

                    response = client.chat.completions.create(

                        model=self.model,

                        messages=[

                            {"role": "system", "content": "You are a precise data extraction assistant."},

                            {"role": "user", "content": prompt}

                        ],

                        max_tokens=2000,

                        temperature=0.2

                    )

                    response_text = response.choices[0].message.content

                except Exception:

                    # Try legacy format as fallback

                    response = openai.ChatCompletion.create(

                        model=self.model,

                        messages=[

                            {"role": "system", "content": "You are a precise data extraction assistant."},

                            {"role": "user", "content": prompt}

                        ],

                        max_tokens=2000,

                        temperature=0.2

                    )

                    response_text = response.choices[0].message.content



                # Parse the response

                try:

                    if "```json" in response_text:

                        json_str = response_text.split("```json", 1)[1].split("```", 1)[0]

                        return json.loads(json_str)

                    elif "```" in response_text:

                        json_str = response_text.split("```", 1)[1].split("```", 1)[0]

                        return json.loads(json_str)

                    else:

                        return json.loads(response_text)

                except json.JSONDecodeError:

                    # Return raw text if JSON parsing fails

                    return {"raw_extraction": response_text}

            except Exception as e:

                logger.error(f"OpenAI extraction error: {e}")

                # Continue to fallbacks



        # Try HuggingFace for extraction

        try:

            structured_data = self.extract_with_huggingface(prompt)

            if structured_data:

                return structured_data

        except Exception as e:

            logger.error(f"HuggingFace extraction error: {e}")



        # Fallback - simple rule-based extraction

        return self.rule_based_extraction(prompt)



    def extract_with_huggingface(self, prompt: str) -> Dict[str, Any]:

        """Use HuggingFace for structured data extraction."""

        # Modified prompt to encourage structured output

        structured_prompt = f"""

        Extract structured information from this text. Output valid JSON.

        

        {prompt}

        

        JSON output:

        ```json

        {{

        """



        try:

            url = "https://api-inference.huggingface.co/models/google/flan-t5-xl"



            headers = {}

            if self.api_key and self.api_key != "your_api_key_here":

                headers["Authorization"] = f"Bearer {self.api_key}"



            response = requests.post(

                url,

                json={"inputs": structured_prompt},

                headers=headers,

                timeout=15

            )



            if response.status_code == 200:

                # Try to complete the JSON and parse it

                result = response.json()[0]["generated_text"]

                json_text = "{\n" + result



                # Add closing brace if missing

                if "}" not in json_text:

                    json_text += "\n}"



                try:

                    return json.loads(json_text)

                except json.JSONDecodeError:

                    # If parsing fails, return a simple structure

                    return {"partial_extraction": result}

            else:

                logger.warning(f"HuggingFace API returned status {response.status_code}")

                return None

        except Exception as e:

            logger.error(f"Error with HuggingFace extraction: {e}")

            return None



    def rule_based_extraction(self, prompt: str) -> Dict[str, Any]:

        """

        Very simple rule-based extraction when APIs fail.

        Parses the extraction prompt and extracts simple entities.

        """

        # Default structure for RPG extraction

        extracted_data = {

            "character_changes": [],

            "location_changes": [],

            "item_changes": [],

            "relationship_changes": [],

            "story_developments": [],

            "current_focus": {

                "characters": [],

                "location": None,

                "items": []

            }

        }



        # Extract the interaction part from the prompt

        interaction_text = ""

        if "USER INPUT:" in prompt and "AI RESPONSE:" in prompt:

            user_section = prompt.split("USER INPUT:", 1)[1]

            user_input = user_section.split("AI RESPONSE:", 1)[0].strip()

            ai_response = user_section.split("AI RESPONSE:", 1)[1].strip()

            interaction_text = user_input + " " + ai_response



        # Simple character detection

        character_patterns = [

            r"([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)",  # Proper names

            r"the ([a-z]+ [a-z]+man)",  # The old man

            r"the ([a-z]+ [a-z]+woman)",  # The young woman

            r"the ([a-z]+)"  # The guard, the merchant, etc.

        ]



        detected_characters = set()

        for pattern in character_patterns:

            import re

            matches = re.findall(pattern, interaction_text)

            detected_characters.update(matches)



        # Add detected characters to current focus

        for character in detected_characters:

            if character not in ["the", "and", "or", "of", "in", "to"]:  # Filter common words

                extracted_data["current_focus"]["characters"].append(character)



        # Look for location mentions

        location_patterns = [r"in the ([a-z]+ [a-z]+)", r"at the ([a-z]+ [a-z]+)"]

        for pattern in location_patterns:

            matches = re.findall(pattern, interaction_text.lower())

            if matches:

                extracted_data["current_focus"]["location"] = matches[0]

                break



        return extracted_data



    def create_entity_description(self, entity_data: Dict[str, Any]) -> str:

        """

        Create a narrative description of an entity.



        Args:

            entity_data: Entity data



        Returns:

            Narrative description

        """

        # Fallback to simple template-based descriptions

        entity_type = entity_data.get("type", "entity")

        name = entity_data.get("name", "Unknown")

        description = entity_data.get("description", "")



        if entity_type == "character":

            traits = entity_data.get("traits", {})

            traits_text = ", ".join(f"{k}: {v}" for k, v in traits.items())



            return f"{name} is a {traits_text} character. {description}"



        elif entity_type == "location":

            features = entity_data.get("features", [])

            features_text = ", ".join(features)



            return f"{name} is a location with {features_text}. {description}"



        elif entity_type == "item":

            properties = entity_data.get("properties", {})

            properties_text = ", ".join(f"{k}: {v}" for k, v in properties.items())



            return f"{name} is an item with {properties_text}. {description}"



        # Default for other entity types

        return f"{name} - {description}"