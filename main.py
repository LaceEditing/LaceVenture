"""

Main entry point for the AI RPG memory system.

"""



import os

import sys

import logging

import argparse

from typing import Dict, Any, Optional



from game_interface import GameInterface

from memory_system import MemorySystem

from llm_interface import LLMInterface

from config import CAMPAIGNS_DIR, LOGS_DIR, DATA_DIR, API_KEY



# Set up logging

logging.basicConfig(

    level=logging.INFO,

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    handlers=[

        logging.FileHandler("rpg_memory_system.log"),

        logging.StreamHandler()

    ]

)



logger = logging.getLogger(__name__)





def setup_directories():

    """Create necessary directories if they don't exist."""

    os.makedirs(DATA_DIR, exist_ok=True)

    os.makedirs(CAMPAIGNS_DIR, exist_ok=True)

    os.makedirs(LOGS_DIR, exist_ok=True)





def parse_arguments():

    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description='AI RPG Memory System')



    parser.add_argument('--campaign', '-c', help='Load specific campaign by ID')

    parser.add_argument('--new', '-n', help='Create new campaign with specified name')

    parser.add_argument('--setup', '-s', help='Path to JSON setup file for new campaign')

    parser.add_argument('--check', action='store_true', help='Run consistency check on specified campaign')

    parser.add_argument('--model', '-m', help='Specify a local model to use (updates config.py)')

    parser.add_argument('--list-models', '-l', action='store_true', help='List available models in assets/models')

    parser.add_argument('--no-model-menu', action='store_true', help='Skip the model selection menu')



    return parser.parse_args()





def list_available_models():

    """List all GGUF models available in the assets/models directory."""

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")



    if not os.path.exists(models_dir):

        return []



    models = []

    for file in os.listdir(models_dir):

        if file.lower().endswith('.gguf'):

            model_path = os.path.join(models_dir, file)

            size_mb = os.path.getsize(model_path) / (1024 * 1024)



            # Add model size category for user-friendly display

            if size_mb < 2000:

                size_category = "Small (Fast)"

            elif size_mb < 5000:

                size_category = "Medium"

            elif size_mb < 15000:

                size_category = "Large"

            else:

                size_category = "Very Large (Slow)"



            models.append((file, model_path, size_mb, size_category))



    # Sort models by size (smallest first) for better UX

    models.sort(key=lambda x: x[2])

    return models



def display_model_selection_menu():

    """Display a menu for selecting models and return the chosen model path or free model name."""

    # Get local models

    local_models = list_available_models()



    # Get free API models from config

    from config import FREE_MODELS



    print("\n===== Model Selection Menu =====")

    print("Select a model to use for this session:")



    # Section 1: Local models

    if local_models:

        print("\n== Local Models (Instant Access) ==")

        for i, (name, path, size, category) in enumerate(local_models):

            print(f"{i+1}. {name} ({size:.1f} MB) - {category}")

    else:

        print("\n== No Local Models Found ==")

        print("To use local models, add GGUF files to the assets/models directory.")



    # Section 2: Free API models

    # Get list of models and sort to put Llama 3 first

    free_model_names = list(FREE_MODELS.keys())

    # Custom sort - put Llama 3 first, then the smaller models, then larger models

    def sort_key(name):

        # Priority order - Llama 3 first, then smaller models before larger ones

        if "Llama 3" in name:

            return 0

        elif "70B" in name or "large" in FREE_MODELS[name]["description"].lower():

            return 3

        elif "Mixtral" in name:

            return 2

        else:

            return 1



    free_model_names.sort(key=sort_key)



    if free_model_names:

        print("\n== Free API Models (Internet Required) ==")

        for i, name in enumerate(free_model_names):

            model_info = FREE_MODELS[name]

            description = model_info["description"] if "description" in model_info else ""



            # Highlight recommended model

            prefix = "★ " if "recommended" in description.lower() else "  "

            print(f"{len(local_models) + i + 1}. {prefix}{name} - {description}")



    # Default option

    total_options = len(local_models) + len(free_model_names)

    print(f"\n{total_options + 1}. Use Default (from config.py)")

    print("q. Quit")



    while True:

        choice = input(f"\nEnter your choice [1-{total_options + 1}] or 'q' to quit: ")



        if choice.lower() == 'q':

            print("Exiting...")

            sys.exit(0)



        try:

            choice_num = int(choice)

            if 1 <= choice_num <= len(local_models):

                # Selected a local model

                return {"type": "local", "path": f"assets/models/{local_models[choice_num-1][0]}"}

            elif len(local_models) < choice_num <= total_options:

                # Selected a free API model

                free_model_index = choice_num - len(local_models) - 1

                selected_free_model = free_model_names[free_model_index]

                return {"type": "free", "name": selected_free_model}

            elif choice_num == total_options + 1:

                # Use default from config

                return {"type": "default"}

            else:

                print(f"Please enter a number between 1 and {total_options + 1}")

        except ValueError:

            print("Please enter a valid number or 'q'")



    return {"type": "default"}



def update_model_config(model_path):

    """Update the config.py file with the provided model path."""

    try:

        with open("config.py", "r") as f:

            config_content = f.read()



        # Update the LOCAL_MODEL_PATH in config

        if "LOCAL_MODEL_PATH" in config_content:

            lines = config_content.split("\n")

            for i, line in enumerate(lines):

                if "LOCAL_MODEL_PATH" in line:

                    lines[i] = f'LOCAL_MODEL_PATH = "{model_path}"  # Path to local GGUF model'

                    break



            # Ensure LLM_PROVIDER is set to "local"

            for i, line in enumerate(lines):

                if "LLM_PROVIDER" in line:

                    lines[i] = 'LLM_PROVIDER = "local"  # Options: "openai", "huggingface", "local"'

                    break



            with open("config.py", "w") as f:

                f.write("\n".join(lines))



            return True

        else:

            logger.error("Cannot find LOCAL_MODEL_PATH in config.py")

            return False

    except Exception as e:

        logger.error(f"Error updating config.py: {e}")

        return False



def main():

    """Main entry point."""

    # Create necessary directories

    setup_directories()



    # Parse command line arguments

    args = parse_arguments()



    # Handle model listing

    if args.list_models:

        models = list_available_models()

        if models:

            print("Available models in assets/models directory:")

            for i, (name, path, size, category) in enumerate(models):

                print(f"{i+1}. {name} ({size:.2f} MB) - {category}")

        else:

            print("No GGUF models found in assets/models directory")

        return



    # Initialize model_path as None (will use default from config.py)

    model_path = None



    # Handle model selection from command line

    if args.model:

        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")



        # Check if it's a model name or a path

        if os.path.exists(args.model):

            # It's a direct path

            model_path = args.model

        elif os.path.exists(os.path.join(models_dir, args.model)):

            # It's a model name in the assets/models directory

            model_path = f"assets/models/{args.model}"

        else:

            # Try to find a model that starts with this name

            found = False

            for file in os.listdir(models_dir):

                if file.lower().startswith(args.model.lower()) and file.lower().endswith('.gguf'):

                    model_path = f"assets/models/{file}"

                    found = True

                    break



            if not found:

                print(f"Model '{args.model}' not found. Available models:")

                models = list_available_models()

                if models:

                    for i, (name, path, size, category) in enumerate(models):

                        print(f"{i+1}. {name} ({size:.2f} MB) - {category}")

                else:

                    print("No models found in assets/models directory")

                return



    # Display model selection menu if no model specified and --no-model-menu not set

    selected_free_model = None



    if not args.model and not args.no_model_menu and not args.check:

        try:

            selection = display_model_selection_menu()

            if selection["type"] == "local":

                model_path = selection["path"]

            elif selection["type"] == "free":

                selected_free_model = selection["name"]

                # No need to update config for free models, they're handled at runtime

        except KeyboardInterrupt:

            print("\nExiting...")

            sys.exit(0)



    # Update config with selected local model if needed

    if model_path:

        print(f"Setting model to: {os.path.basename(model_path)}")

        update_model_config(model_path)



        # Reload config after update

        import importlib

        import config

        importlib.reload(config)

        from config import LLM_PROVIDER, LOCAL_MODEL_PATH, FREE_MODELS, API_KEY

    else:

        # Use existing config

        from config import LLM_PROVIDER, LOCAL_MODEL_PATH, FREE_MODELS, API_KEY



    # Check if we're using local model or API

    if LLM_PROVIDER == "local":

        # Only show this message if we're not just doing a consistency check

        if not (args.check and args.campaign):

            print(f"Using local LLM: {os.path.basename(LOCAL_MODEL_PATH)}")

    else:

        # Check API key for non-local providers

        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:

            print("Warning: OPENAI_API_KEY environment variable not set.")

            print("You can set it with: export OPENAI_API_KEY=your_key_here")



            use_key = input("Would you like to enter your API key now? (y/n): ")

            if use_key.lower() == 'y':

                api_key = input("Enter your OpenAI API key: ")

                os.environ["OPENAI_API_KEY"] = api_key



    # Create LLM interface with the selected free model if applicable

    if selected_free_model:

        print(f"Using free model: {selected_free_model}")

        try:

            model_info = FREE_MODELS[selected_free_model]

            # Ask for API key if the provider needs one and none is provided

            if model_info["provider"] == "together" and (not API_KEY or API_KEY == ""):

                print("\nTogether.ai API key is recommended for better service.")

                print("You can continue without one, but you may hit rate limits.")

                use_key = input("Would you like to enter your Together.ai API key? (y/n): ")

                if use_key.lower() == 'y':

                    api_key = input("Enter your Together.ai API key: ")

                else:

                    api_key = ""  # Empty string means guest access

            else:

                api_key = API_KEY  # Use the configured API key from config.py



            # Create interface with the free model

            llm = LLMInterface(api_key=api_key, selected_free_model=selected_free_model)



        except KeyError:

            print(f"Free model '{selected_free_model}' not found in configuration.")

            print("Using default model from config.py instead.")

            llm = LLMInterface()

    else:

        # Create standard LLM interface

        llm = LLMInterface()



    # Print confirmation based on which LLM is being used

    if llm.provider == "local":

        if hasattr(llm, 'local_llm') and llm.local_llm is not None:

            print(f"✓ Local LLM loaded successfully")

        else:

            print("⚠ Local LLM failed to load, falling back to rule-based responses")

            print("  Check that the model file exists and llama-cpp-python is installed")

    elif llm.provider == "openai":

        print(f"Using OpenAI API with model: {llm.model}")

    elif llm.provider == "huggingface":

        print(f"Using Hugging Face with model: {llm.model}")

    elif llm.provider == "together":

        print(f"Using Together.ai with model: {llm.model_id}")

        print("Response generation may take a moment as it uses an external API.")

    elif llm.provider == "ollama":

        print(f"Using Ollama with model: {llm.model_id or llm.model}")



    # Handle command line arguments for campaigns

    if args.campaign and args.check:

        # Run consistency check on specified campaign

        memory_system = MemorySystem(llm_interface=llm)

        if memory_system.load_campaign(args.campaign):

            print(f"Running consistency check on campaign: {memory_system.campaign_name}")

            results = memory_system.run_consistency_check()



            print(f"\nFound {results['counts']['total']} potential inconsistencies:")

            print(f"- High severity: {results['counts']['by_severity']['high']}")

            print(f"- Medium severity: {results['counts']['by_severity']['medium']}")

            print(f"- Low severity: {results['counts']['by_severity']['low']}")



            if results['counts']['total'] > 0:

                print("\nInconsistencies by type:")

                for type_key, count in results['counts']['by_type'].items():

                    print(f"- {type_key}: {count}")



                print("\nDetailed inconsistencies:")

                for inconsistency in results['inconsistencies']:

                    entity_id = inconsistency.get("entity_id", "Unknown")

                    entity_name = inconsistency.get("entity_name", entity_id)

                    description = inconsistency.get("description", "No description")

                    severity = inconsistency.get("severity", "medium")



                    print(f"- [{severity.upper()}] {entity_name}: {description}")

        else:

            print(f"Campaign not found: {args.campaign}")

    elif args.new:

        # Create new campaign

        memory_system = MemorySystem(campaign_name=args.new, llm_interface=llm)



        if args.setup and os.path.exists(args.setup):

            try:

                import json

                with open(args.setup, "r") as f:

                    setup_data = json.load(f)



                memory_system.create_campaign(args.new, setup_data)

                print(f"Created campaign: {args.new}")

            except Exception as e:

                logger.error(f"Error creating campaign: {e}")

                print(f"Error creating campaign: {e}")

                memory_system.create_campaign(args.new, {})

        else:

            memory_system.create_campaign(args.new, {})

            print(f"Created empty campaign: {args.new}")

    elif args.campaign:

        # Load specified campaign

        memory_system = MemorySystem(llm_interface=llm)

        if memory_system.load_campaign(args.campaign):

            print(f"Loaded campaign: {memory_system.campaign_name}")



            # Start the game interface with loaded campaign

            interface = GameInterface()

            interface.memory_system = memory_system

            interface.campaign_loaded = True

            interface.cmdloop()

        else:

            print(f"Campaign not found: {args.campaign}")

    else:

        # No specific campaign - start the game interface

        interface = GameInterface()

        interface.cmdloop()



    # Handle command line arguments

    if args.campaign and args.check:

        # Run consistency check on specified campaign

        memory_system = MemorySystem(llm_interface=llm)

        if memory_system.load_campaign(args.campaign):

            print(f"Running consistency check on campaign: {memory_system.campaign_name}")

            results = memory_system.run_consistency_check()



            print(f"\nFound {results['counts']['total']} potential inconsistencies:")

            print(f"- High severity: {results['counts']['by_severity']['high']}")

            print(f"- Medium severity: {results['counts']['by_severity']['medium']}")

            print(f"- Low severity: {results['counts']['by_severity']['low']}")



            if results['counts']['total'] > 0:

                print("\nInconsistencies by type:")

                for type_key, count in results['counts']['by_type'].items():

                    print(f"- {type_key}: {count}")



                print("\nDetailed inconsistencies:")

                for inconsistency in results['inconsistencies']:

                    entity_id = inconsistency.get("entity_id", "Unknown")

                    entity_name = inconsistency.get("entity_name", entity_id)

                    description = inconsistency.get("description", "No description")

                    severity = inconsistency.get("severity", "medium")



                    print(f"- [{severity.upper()}] {entity_name}: {description}")

        else:

            print(f"Campaign not found: {args.campaign}")

    elif args.new:

        # Create new campaign

        memory_system = MemorySystem(campaign_name=args.new, llm_interface=llm)



        if args.setup and os.path.exists(args.setup):

            try:

                import json

                with open(args.setup, "r") as f:

                    setup_data = json.load(f)



                memory_system.create_campaign(args.new, setup_data)

                print(f"Created campaign: {args.new}")

            except Exception as e:

                logger.error(f"Error creating campaign: {e}")

                print(f"Error creating campaign: {e}")

                memory_system.create_campaign(args.new, {})

        else:

            memory_system.create_campaign(args.new, {})

            print(f"Created empty campaign: {args.new}")

    elif args.campaign:

        # Load specified campaign

        memory_system = MemorySystem(llm_interface=llm)

        if memory_system.load_campaign(args.campaign):

            print(f"Loaded campaign: {memory_system.campaign_name}")



            # Start the game interface with loaded campaign

            interface = GameInterface()

            interface.memory_system = memory_system

            interface.campaign_loaded = True

            interface.cmdloop()

        else:

            print(f"Campaign not found: {args.campaign}")

    else:

        # No specific campaign - start the game interface

        interface = GameInterface()

        interface.cmdloop()





if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print("\nExiting...")

        sys.exit(0)

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        print(f"An error occurred: {e}")

        sys.exit(1)