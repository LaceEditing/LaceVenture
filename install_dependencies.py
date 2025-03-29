u#!/usr/bin/env python3
"""
Helper script to install all required dependencies for AI Narrative RPG system.
This installs packages for both local LLM support and free API models.
"""

import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version meets the requirements."""
    major, minor, _ = platform.python_version_tuple()
    if int(major) < 3 or (int(major) == 3 and int(minor) < 8):
        print("Error: Python 3.8 or higher is required.")
        print(f"Current Python version: {platform.python_version()}")
        return False
    return True

def install_dependencies():
    """Install required dependencies from requirements.txt."""
    print("Installing core dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Core dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies from requirements.txt")
        return False

def install_llama_cpp():
    """Install llama-cpp-python package for local LLM support."""
    print("\nInstalling local LLM support...")
    try:
        # Check if CUDA is available and ask the user if they want to use it
        use_cuda = input("Would you like to install with CUDA support for GPU acceleration? (y/n): ").lower() == 'y'
        
        if use_cuda:
            print("Installing llama-cpp-python with CUDA support...")
            cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--force-reinstall", "--upgrade", "--no-cache-dir"]
            env = {"CMAKE_ARGS": "-DLLAMA_CUBLAS=on"}
            subprocess.check_call(cmd, env=env)
        else:
            print("Installing llama-cpp-python without GPU acceleration...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "llama-cpp-python"])
            
        print("✓ Local LLM support installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install llama-cpp-python")
        print("You may need to install it manually:")
        print("  pip install llama-cpp-python")
        print("  # Or with CUDA support:")
        print("  CMAKE_ARGS=\"-DLLAMA_CUBLAS=on\" pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir")
        return False

def install_api_support():
    """Install packages for API model support."""
    print("\nInstalling API model support...")
    try:
        # Install Together.ai API client
        print("Installing Together.ai API client...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "together"])
        print("✓ Together.ai API support installed successfully")
        
        # Optional: Install Ollama client
        install_ollama = input("\nWould you like to install Ollama support for local API models? (y/n): ").lower() == 'y'
        if install_ollama:
            print("Installing Ollama client...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama"])
            print("✓ Ollama support installed successfully")
        
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install API support packages")
        return False

def main():
    """Main entry point."""
    print("=== AI Narrative RPG System Dependency Installer ===\n")
    
    if not check_python_version():
        sys.exit(1)
    
    # Install core dependencies first
    if not install_dependencies():
        print("\nFailed to install core dependencies. Please fix the errors and try again.")
        sys.exit(1)
    
    # Install local LLM support (optional)
    install_local = input("\nWould you like to install support for local LLMs? (y/n): ").lower() == 'y'
    if install_local:
        install_llama_cpp()
    
    # Install API support
    install_api = input("\nWould you like to install support for free API models? (y/n): ").lower() == 'y'
    if install_api:
        install_api_support()
    
    print("\n=== Installation Complete ===")
    print("You can now run the system with:")
    print("  python main.py")
    print("\nIf you want to configure a specific model:")
    print("  python setup_local_llm.py")

if __name__ == "__main__":
    main()