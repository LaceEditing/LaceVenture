#!/usr/bin/env python3
"""
Setup script for local LLM support in AINarrative.
This script helps install the required dependencies and validates the configuration.
"""

import os
import sys
import subprocess
import argparse

def check_requirements():
    """Check if necessary packages are installed."""
    try:
        import llama_cpp
        print("✓ llama-cpp-python is installed")
        return True
    except ImportError:
        print("✗ llama-cpp-python is not installed")
        return False

def install_requirements():
    """Install required packages."""
    print("\nInstalling required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "llama-cpp-python"])
        print("✓ Successfully installed llama-cpp-python")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install llama-cpp-python")
        print("You may need to install it manually with GPU support:")
        print("  pip install llama-cpp-python")
        print("  # Or with CUDA support:")
        print("  CMAKE_ARGS=\"-DLLAMA_CUBLAS=on\" pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir")
        return False

def ensure_assets_directory():
    """Ensure assets/models directory exists."""
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    models_dir = os.path.join(assets_dir, "models")
    
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"✓ Assets directory ready: {models_dir}")
    return models_dir

def update_config(model_path):
    """Update the config.py file with the provided model path."""
    if not os.path.exists(model_path):
        print(f"✗ Model file not found at: {model_path}")
        return False
    
    # Get the model filename
    model_filename = os.path.basename(model_path)
    
    # Determine if we need to copy the model to assets/models
    models_dir = ensure_assets_directory()
    destination_path = os.path.join(models_dir, model_filename)
    
    # If model is not already in assets/models, suggest copying it
    if model_path != destination_path and not os.path.exists(destination_path):
        should_copy = input(f"\nWould you like to copy the model to {models_dir}? (y/n): ").lower() == 'y'
        
        if should_copy:
            try:
                print(f"Copying model to {destination_path}...")
                print("This may take a while for large models...")
                import shutil
                shutil.copy2(model_path, destination_path)
                print(f"✓ Model copied to {destination_path}")
                model_path = f"assets/models/{model_filename}"  # Use relative path in config
            except Exception as e:
                print(f"✗ Error copying model: {e}")
                print("Using original model path instead")
    elif os.path.exists(destination_path) and model_path != destination_path:
        # Model already exists in assets/models, use that path
        print(f"✓ Model already exists in assets directory")
        model_path = f"assets/models/{model_filename}"  # Use relative path in config
    
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
            
            # Also update LLM_PROVIDER to ensure it's set to "local"
            for i, line in enumerate(lines):
                if "LLM_PROVIDER" in line:
                    lines[i] = 'LLM_PROVIDER = "local"  # Options: "openai", "huggingface", "local"'
                    break
            
            # Also update MODEL_NAME to match the model name
            model_name = model_filename.split(".")[0]  # Remove file extension
            for i, line in enumerate(lines):
                if "MODEL_NAME" in line and "LOCAL_MODEL" not in line:
                    lines[i] = f'MODEL_NAME = "{model_name}"  # Default model name'
                    break
            
            with open("config.py", "w") as f:
                f.write("\n".join(lines))
        else:
            print("✗ Cannot find LOCAL_MODEL_PATH in config.py")
            return False
        
        print(f"✓ Updated config.py with model path: {model_path}")
        return True
    except Exception as e:
        print(f"✗ Error updating config.py: {e}")
        return False

def validate_model(model_path):
    """Validate if the model file exists and appears to be a GGUF file."""
    if not os.path.exists(model_path):
        print(f"✗ Model file not found at: {model_path}")
        return False
    
    # Simple validation - check file extension and size
    if not model_path.lower().endswith(".gguf"):
        print(f"✗ File does not have .gguf extension: {model_path}")
        print("  The file might still work if it's compatible with llama-cpp-python")
    
    # Check file size (GGUF models are typically at least several hundred MB)
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    if size_mb < 100:
        print(f"⚠ Warning: Model file is unusually small ({size_mb:.2f} MB)")
        print("  This might not be a valid GGUF model file")
    else:
        print(f"✓ Model file size looks reasonable: {size_mb:.2f} MB")
    
    return True

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
            models.append((file, model_path, size_mb))
    
    return models

def show_free_models():
    """Display information about available free API models."""
    try:
        from config import FREE_MODELS
        if FREE_MODELS:
            print("\n=== Available Free API Models ===")
            print("These models can be used without downloading large files.")
            print("Select them from the model menu when starting the game.\n")
            
            for i, (name, info) in enumerate(FREE_MODELS.items()):
                provider = info.get("provider", "unknown")
                model_id = info.get("model_id", "unknown")
                description = info.get("description", "")
                
                print(f"{i+1}. {name}")
                print(f"   Provider: {provider}")
                print(f"   Model ID: {model_id}")
                if description:
                    print(f"   Description: {description}")
                print()
                
            print("To use these models, you'll need internet access.")
            print("For best performance, consider getting an API key from Together.ai")
            return True
        else:
            print("No free API models are configured.")
            return False
    except (ImportError, AttributeError):
        print("Could not load FREE_MODELS from config.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Setup local LLM support for AINarrative")
    parser.add_argument("--model", "-m", help="Path to GGUF model file")
    parser.add_argument("--install", "-i", action="store_true", help="Install required dependencies")
    parser.add_argument("--list", "-l", action="store_true", help="List available models in assets/models")
    parser.add_argument("--show-free", "-f", action="store_true", help="Show available free API models")
    args = parser.parse_args()
    
    print("=== AINarrative LLM Setup ===\n")
    
    # Show free models if requested
    if args.show_free:
        show_free_models()
        return
    
    # Ensure assets/models directory exists
    models_dir = ensure_assets_directory()
    
    # List available models if requested
    if args.list:
        models = list_available_models()
        if models:
            print(f"=== Local Models in {models_dir} ===")
            for i, (name, path, size) in enumerate(models):
                print(f"{i+1}. {name} ({size:.2f} MB)")
            
            # Also show free models
            print("\nNote: In addition to these local models, free API models are also available.")
            print("To see them, run: python setup_local_llm.py --show-free")
        else:
            print(f"No GGUF models found in {models_dir}")
            print("\nConsider downloading GGUF models, or use the free API models:")
            print("Run: python setup_local_llm.py --show-free")
        return
    
    # Check requirements
    has_requirements = check_requirements()
    
    # Install requirements if needed
    if not has_requirements and (args.install or input("\nInstall required packages? (y/n): ").lower() == 'y'):
        has_requirements = install_requirements()
    
    if not has_requirements:
        print("\n✗ Required packages are not installed. Setup cannot continue.")
        return
    
    # Check for available models
    available_models = list_available_models()
    
    # Update config with model path
    model_path = args.model
    if not model_path:
        if available_models:
            print("\nAvailable models:")
            for i, (name, path, size) in enumerate(available_models):
                print(f"{i+1}. {name} ({size:.2f} MB)")
            
            choice = input("\nSelect a model number or enter a custom path: ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(available_models):
                    model_path = available_models[index][1]
                else:
                    model_path = input("\nEnter the path to your GGUF model file: ")
            except ValueError:
                model_path = choice
        else:
            model_path = input("\nEnter the path to your GGUF model file: ")
    
    if model_path:
        # Convert to absolute path if relative and not already in assets/models
        if not os.path.isabs(model_path) and not model_path.startswith("assets/models"):
            model_path = os.path.abspath(model_path)
        
        if validate_model(model_path):
            update_config(model_path)
    
    print("\n=== Setup Complete ===")
    print("To run the application with the local LLM:")
    print("1. The config has been updated with LLM_PROVIDER = \"local\"")
    print("2. Run the application: python main.py")
    print("\nEnjoy your local AI storytelling experience!")

if __name__ == "__main__":
    main()