import sys
import os
import json
import glob
import re
import hashlib
import subprocess
import platform
import tempfile
import requests
from functools import lru_cache

from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel,
                             QComboBox, QListWidget, QMessageBox, QFormLayout, QSpinBox,
                             QSplitter, QScrollArea, QFrame, QDialog, QDialogButtonBox,
                             QCheckBox, QTextBrowser, QGroupBox, QProgressDialog)
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject

# Import the needed libraries from original code
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# Directory for storing game stories
STORIES_DIR = "rpg_stories"
os.makedirs(STORIES_DIR, exist_ok=True)

# Response cache
response_cache = {}

# Terminal colors for the DM output
SYSTEM_COLOR = "#4CAF50"  # Green
DM_NAME_COLOR = "#00BCD4"  # Cyan
DM_TEXT_COLOR = "#80DEEA"  # Light Cyan
PLAYER_COLOR = "#FFC107"  # Amber

# Adjusted DM prompt template with improved role clarity
dm_template = """
You ARE the Dungeon Master for this {genre} RPG set in {world_name}. 
DO NOT give advice about how to be a DM - you ARE the DM.
DO NOT refer to yourself as writing a guide or giving tips.
DIRECTLY narrate the story and respond to the player's actions.

Your job is to:

1. Create an immersive world with rich descriptions that engage all senses
2. Portray NPCs with consistent personalities, goals, and knowledge
3. Present appropriate challenges and opportunities for character development
4. Maintain narrative continuity and remember details from previous sessions
5. Apply game rules fairly while prioritizing storytelling and player enjoyment
6. Adapt the story based on player choices to create a truly interactive experience

CRITICAL OUTPUT REQUIREMENTS:
- BREVITY: Keep responses extremely short, 1 to 3 sentences maximum
- VARIETY: Never use similar sentence structures back-to-back
- PRECISION: Use specific, evocative details rather than general descriptions, but avoid being too verbose
- UNIQUENESS: Avoid reusing phrases, descriptions, or scene transitions
- FREEDOM: Only give the player specific choices when absolutely necessary, otherwise always simply ask "What will you do?" to end your output
- GAMEPLAY: You are the Dungeon Master, not a guide writer. Never break character.

CONTENT RATING GUIDELINES - THIS STORY HAS A "{rating}" RATING:
- E rating: Keep content family-friendly. Avoid graphic violence, frightening scenarios, sexual content, and strong language.
- T rating: Moderate content is acceptable. Some violence, dark themes, mild language, and light romantic implications allowed, but nothing explicit or graphic.
- M rating: Mature content is permitted. You may include graphic violence, sexual themes, intense scenarios, and strong language as appropriate to the story.

PLOT PACING GUIDELINES - THIS STORY HAS A "{plot_pace}" PACING:
- Fast-paced: Maintain steady forward momentum with regular plot developments and challenges. Focus primarily on action, goals, and advancing the main storyline. Character development should happen through significant events rather than quiet moments. Keep the story moving forward with new developments in most scenes.
- Balanced: Create a rhythm alternating between plot advancement and character moments. Allow time for reflection and relationship development between significant story beats. Mix everyday interactions with moderate plot advancement. Ensure characters have time to process events before introducing new major developments.
- Slice-of-life: Deliberately slow down plot progression in favor of everyday moments and mundane interactions. Focus on character relationships, personal growth, and daily activities rather than dramatic events. Allow extended periods where characters simply live their lives, with minimal story progression. Prioritize small, meaningful character moments and ordinary situations. Major plot developments should be rare and spaced far apart, with emphasis on how characters experience their everyday world.

DYNAMIC WORLD CREATION:
You are encouraged to create new elements when appropriate to enhance the story:
- Create new NPCs with distinct personalities, motivations, and relationships
- Develop new locations as the player explores the world, but introduce them slowly and gradually
- Add items, quests, and other world elements that emerge naturally from the narrative
- Any new elements should be consistent with the established world and plot pacing

When you introduce a new element:
- Provide a clear, vivid description that fits the world and tone
- Connect it logically to existing elements in the story
- Remember details about the new elements and reference them consistently
- New elements should enhance but not overshadow the player's experience

When describing environments:
- Focus on one distinctive sensory detail rather than cataloging the entire scene
- Mention only elements the player can directly interact with
- Use fresh, unexpected descriptors

When portraying NPCs:
- Let their actions reveal their character instead of explaining their traits explicitly
- Vary speech patterns and vocabulary between different characters, while adhering to their personality
- Use minimal dialogue tags
- Keep characters consistent with their personality and motivations

The adventure takes place in a {setting_description}. The tone is {tone}.

Current game state:
{context}

Player: {question}

Dungeon Master:
"""

# Simplified memory update prompt
simplified_memory_template = """
Based on this exchange:
Player: {player_input}
DM: {dm_response}

Extract 1-2 key points about:
- Character development
- Relationships
- Plot developments
- Environment details

Format as bullet points.
"""


class OllamaInstallerThread(QThread):
    """Thread for installing Ollama to prevent UI freezing"""
    progress_update = pyqtSignal(str)
    installation_complete = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.system = platform.system()

    def run(self):
        """Run the Ollama installation process"""
        try:
            self.progress_update.emit("Checking system compatibility...")

            if self.system == "Windows":
                self.install_ollama_windows()
            elif self.system == "Darwin":  # macOS
                self.install_ollama_macos()
            elif self.system == "Linux":
                self.install_ollama_linux()
            else:
                self.installation_complete.emit(False, f"Unsupported operating system: {self.system}")
                return

            self.progress_update.emit("Verifying installation...")
            if self.check_ollama_installed():
                self.installation_complete.emit(True, "Ollama installed successfully!")
            else:
                self.installation_complete.emit(False,
                                                "Installation completed but Ollama is not detected. You may need to restart your computer.")

        except Exception as e:
            self.installation_complete.emit(False, f"Installation failed: {str(e)}")

    def check_ollama_installed(self):
        """Check if Ollama is installed and working"""
        try:
            result = subprocess.run(['ollama', 'list'],
                                    capture_output=True,
                                    text=True,
                                    timeout=10)
            return result.returncode == 0
        except:
            return False

    def install_ollama_windows(self):
        """Install Ollama on Windows"""
        self.progress_update.emit("Downloading Ollama installer for Windows...")

        # Download the installer
        installer_url = "https://ollama.com/download/ollama-installer.exe"
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "ollama-installer.exe")

        response = requests.get(installer_url, stream=True)
        with open(installer_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        self.progress_update.emit("Running installer (this may take a few minutes)...")

        # Run the installer silently
        subprocess.run([installer_path, "/S"], check=True)

        # Update PATH for the current process
        self.progress_update.emit("Updating environment variables...")
        if "ProgramFiles" in os.environ:
            ollama_path = os.path.join(os.environ["ProgramFiles"], "Ollama")
            if ollama_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + ollama_path

    def install_ollama_macos(self):
        """Install Ollama on macOS"""
        self.progress_update.emit("Installing Ollama for macOS...")

        # Check if Homebrew is installed
        try:
            subprocess.run(['brew', '--version'], check=True, capture_output=True)
            # Install using Homebrew
            self.progress_update.emit("Installing via Homebrew...")
            subprocess.run(['brew', 'install', 'ollama'], check=True)
        except:
            # Direct installation script
            self.progress_update.emit("Installing via curl script...")
            subprocess.run(['curl', '-fsSL', 'https://ollama.com/install.sh', '|', 'sh'], check=True, shell=True)

    def install_ollama_linux(self):
        """Install Ollama on Linux"""
        self.progress_update.emit("Installing Ollama for Linux...")

        # Using the official installation script
        subprocess.run(['curl', '-fsSL', 'https://ollama.com/install.sh', '|', 'sh'], check=True, shell=True)


class ModelDownloaderThread(QThread):
    """Thread for downloading Ollama models"""
    progress_update = pyqtSignal(str)
    download_complete = pyqtSignal(bool, str)

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name

    def run(self):
        """Run the model download process"""
        try:
            self.progress_update.emit(f"Downloading {self.model_name} model...")

            # Pull the model using ollama
            result = subprocess.run(['ollama', 'pull', self.model_name],
                                    capture_output=True,
                                    text=True,
                                    check=True)

            self.progress_update.emit("Verifying model...")
            if self.check_model_available():
                self.download_complete.emit(True, f"{self.model_name} downloaded successfully!")
            else:
                self.download_complete.emit(False, f"Download completed but {self.model_name} is not detected.")

        except Exception as e:
            self.download_complete.emit(False, f"Download failed: {str(e)}")

    def check_model_available(self):
        """Check if the model is available"""
        try:
            result = subprocess.run(['ollama', 'list'],
                                    capture_output=True,
                                    text=True)
            return self.model_name in result.stdout
        except:
            return False


def get_available_ollama_models():
    """Get a list of available Ollama models on the system"""
    try:
        # First try the newer JSON format
        result = subprocess.run(['ollama', 'list', '--json'],
                                capture_output=True, text=True)

        # Check if command was successful
        if result.returncode == 0:
            try:
                # Parse the JSON output
                models_data = json.loads(result.stdout)

                # Check if 'models' key exists
                if 'models' in models_data:
                    models = [model['name'] for model in models_data['models']]
                    if models:
                        return models
            except json.JSONDecodeError:
                # JSON parsing failed, output might not be in JSON format
                print("Warning: Could not parse JSON output from 'ollama list --json'")

        # If JSON approach failed, try the standard format
        result = subprocess.run(['ollama', 'list'],
                                capture_output=True, text=True)

        if result.returncode == 0:
            # Parse the standard output format
            lines = result.stdout.strip().split('\n')

            # Skip the header line if it exists
            if lines and "NAME" in lines[0] and "ID" in lines[0]:
                lines = lines[1:]

            # Extract model names (first column in each line)
            models = []
            for line in lines:
                if line.strip():
                    # Split by whitespace and take the first part
                    parts = line.split()
                    if parts:
                        models.append(parts[0])

            if models:
                return models

        # Both approaches failed, return default list
        return ["llama3", "mistral-small", "dolphin-mixtral", "gemma", "llama2"]

    except Exception as e:
        print(f"Error getting Ollama models: {e}")
        # Return some default models that are likely to be available
        return ["llama3", "mistral-small", "dolphin-mixtral", "gemma", "llama2"]


def get_faster_model(model_name):
    """Configure Ollama model with parameters optimized for speed"""
    return OllamaLLM(
        model=model_name,
        temperature=0.7,  # Slightly reduced for faster generation
        num_predict=100,  # Limit token count for quicker responses
        repeat_penalty=1.1,  # Discourage repetition for more efficient output
        top_k=40,  # Limit token selection for faster generation
        top_p=0.9,  # Use nucleus sampling for efficiency
    )


def get_story_path(story_name):
    """Get the file path for a story"""
    safe_name = "".join([c if c.isalnum() else "_" for c in story_name])
    return os.path.join(STORIES_DIR, f"{safe_name}.json")


def init_game_state(player_input):
    """Initialize a new game state based on player input"""
    # Extract details from player input
    pc_name = player_input["character_name"]
    pc_race = player_input["character_race"]
    pc_class = player_input["character_class"]
    world_name = player_input["world_name"]
    genre = player_input["genre"]
    setting = player_input["setting"]
    tone = player_input["tone"]
    rating = player_input["rating"]
    plot_pace = player_input["plot_pace"]

    # Create default game state
    game_state = {
        "game_info": {
            "title": player_input["story_title"],
            "world_name": world_name,
            "genre": genre,
            "setting": setting,
            "tone": tone,
            "rating": rating,
            "plot_pace": plot_pace,
            "game_system": f"{genre} RPG",
            "session_count": 1,
            "current_location": "starting_location",
            "current_quest": "main_quest",
            "time_of_day": "morning",
            "days_passed": 0
        },
        "player_characters": {
            "hero": {
                "name": pc_name,
                "race": pc_race,
                "class": pc_class,
                "level": 1,
                "abilities": player_input.get("abilities", ["perception", "persuasion"]),
                "inventory": ["basic_equipment", "rations"],
                "health": 20,
                "max_health": 20,
                "gold": 15,
                "experience": 0,
                "relationships": {},
                "quests": ["main_quest"],
                "character_traits": player_input.get("character_traits", ["determined"])
            }
        },
        "npcs": {},
        "locations": {
            "starting_location": {
                "name": player_input.get("starting_location_name", f"{world_name} Starting Area"),
                "description": player_input.get("starting_location_description",
                                                "You find yourself in a new area, ready to begin your adventure."),
                "ambience": "The environment sets the mood for your adventure.",
                "connected_to": [],
                "npcs_present": [],
                "points_of_interest": [],
                "secrets": [],
                "available_quests": ["main_quest"],
                "visited": True
            }
        },
        "items": {},
        "quests": {
            "main_quest": {
                "name": player_input.get("quest_name", "The Beginning"),
                "description": player_input.get("quest_description",
                                                "Your adventure begins here. What will you discover?"),
                "status": "active",
                "giver": "narrator",
                "steps": [
                    {"id": "begin_adventure", "description": "Start your adventure", "completed": False}
                ],
                "difficulty": "beginner",
                "time_sensitive": False
            }
        },
        "conversation_history": [
            {
                "session": 1,
                "exchanges": []
            }
        ],
        "world_facts": player_input.get("world_facts", [f"{world_name} awaits exploration"]),
        "story_arcs": {
            "main_arc": {
                "description": "The main storyline",
                "status": "active",
                "related_quests": ["main_quest"],
                "plot_twists": []
            }
        },
        "narrative_memory": {
            "world_facts": [],
            "character_development": [],
            "relationships": [],
            "plot_developments": [],
            "player_decisions": [],
            "environment_details": [],
            "conversation_details": []
        },
        "important_updates": []  # Store critical plot/character updates to notify player
    }
    game_state["game_info"]["model_name"] = player_input.get("model_name",
                                                             "mistral-small")  # Default to mistral-small if not specified

    # Add custom NPCs if provided
    for npc in player_input.get("npcs", []):
        npc_id = "npc_" + "".join([c.lower() if c.isalnum() else "_" for c in npc.get("name", "unknown")])
        game_state["npcs"][npc_id] = {
            "name": npc.get("name", "Unknown"),
            "race": npc.get("race", "Unknown"),
            "description": npc.get("description", "A mysterious figure"),
            "location": "starting_location",
            "disposition": npc.get("disposition", "neutral"),
            "motivation": npc.get("motivation", "unknown"),
            "knowledge": [],
            "relationships": {},
            "dialogue_style": npc.get("dialogue_style", "speaks normally")
        }
        # Add NPC to starting location
        game_state["locations"]["starting_location"]["npcs_present"].append(npc_id)

    return game_state


def save_game_state(game_state, story_name):
    """Save the game state to a JSON file"""
    file_path = get_story_path(story_name)
    with open(file_path, 'w') as f:
        json.dump(game_state, f, indent=2)
    print(f"Game saved to {file_path}")


def load_game_state(story_name):
    """Load the game state from a JSON file"""
    file_path = get_story_path(story_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading game state: {e}")
            return None
    return None


def list_stories():
    """List all available stories"""
    stories = glob.glob(os.path.join(STORIES_DIR, "*.json"))
    result = []

    for story_path in stories:
        try:
            with open(story_path, 'r') as f:
                data = json.load(f)
                story_name = data.get("game_info", {}).get("title", "Unknown")
                result.append((os.path.basename(story_path)[:-5], story_name))
        except:
            # Skip files that can't be read properly
            pass

    return result


def delete_story(story_name):
    """Delete a story file"""
    file_path = get_story_path(story_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting story: {e}")
    return False


def generate_context(game_state, max_history=8):
    """Generate context string from game state for the LLM, with enhanced detail recall"""
    context = "IMPORTANT: You ARE the Dungeon Master running this game. DO NOT give advice about being a DM. DIRECTLY narrate the story and respond to players.\n\n"

    # Add game info
    context += f"Game: {game_state['game_info']['title']}\n"
    context += f"World: {game_state['game_info']['world_name']}\n"
    context += f"Genre: {game_state['game_info']['genre']}\n"
    context += f"Rating: {game_state['game_info'].get('rating', 'T')}\n"  # Default to T if rating not present
    context += f"Plot Pacing: {game_state['game_info'].get('plot_pace', 'Balanced')}\n"  # Default to Balanced if not present
    current_loc_id = game_state['game_info']['current_location']
    context += f"Current location: {game_state['locations'][current_loc_id]['name']}\n"
    context += f"Time: {game_state['game_info']['time_of_day']}, Day {game_state['game_info']['days_passed']}\n\n"

    # Add current location info
    location = game_state['locations'][current_loc_id]
    context += f"Current location - {location['name']}: {location['description']}\n"
    context += f"Ambience: {location['ambience']}\n"

    # Add NPCs present at location
    if location['npcs_present']:
        context += "NPCs present:\n"
        for npc_id in location['npcs_present']:
            npc = game_state['npcs'][npc_id]
            context += f"- {npc['name']}: {npc['description']}\n  Disposition: {npc['disposition']}, Motivation: {npc['motivation']}\n  Dialogue style: {npc['dialogue_style']}\n"

    # Add active quest info
    current_quest_id = game_state['game_info']['current_quest']
    if current_quest_id:
        quest = game_state['quests'][current_quest_id]
        context += f"\nCurrent quest - {quest['name']}: {quest['description']}\n"
        context += "Quest progress:\n"
        for step in quest['steps']:
            status = "✓" if step['completed'] else "□"
            context += f"- {status} {step['description']}\n"

    # Add player character info
    pc_id = list(game_state['player_characters'].keys())[0]
    pc = game_state['player_characters'][pc_id]
    context += f"\nPlayer character {pc['name']}:\n"
    context += f"Level {pc['level']} {pc['race']} {pc['class']}\n"
    context += f"Health: {pc['health']}/{pc['max_health']}\n"
    if 'character_traits' in pc:
        context += f"Character traits: {', '.join(pc['character_traits'])}\n"
    context += f"Abilities: {', '.join(pc['abilities'])}\n"
    context += f"Inventory: {', '.join(pc['inventory'])}\n"
    context += f"Gold: {pc['gold']}\n"

    # Add narrative memory
    context += "\n=== NARRATIVE MEMORY ===\n"

    # World facts
    if game_state['narrative_memory']['world_facts']:
        context += "World facts:\n"
        for fact in game_state['narrative_memory']['world_facts']:
            context += f"- {fact}\n"

    # Character development
    if game_state['narrative_memory']['character_development']:
        context += "Character development:\n"
        for development in game_state['narrative_memory']['character_development']:
            context += f"- {development}\n"

    # Relationships
    if game_state['narrative_memory']['relationships']:
        context += "Relationships:\n"
        for relationship in game_state['narrative_memory']['relationships']:
            context += f"- {relationship}\n"

    # Plot developments
    if game_state['narrative_memory']['plot_developments']:
        context += "Plot developments:\n"
        for development in game_state['narrative_memory']['plot_developments']:
            context += f"- {development}\n"

    # Player decisions
    if game_state['narrative_memory']['player_decisions']:
        context += "Important player decisions:\n"
        for decision in game_state['narrative_memory']['player_decisions']:
            context += f"- {decision}\n"

    # Environment details (new category)
    if 'environment_details' in game_state['narrative_memory'] and game_state['narrative_memory'][
        'environment_details']:
        context += "Environment details:\n"
        for detail in game_state['narrative_memory']['environment_details']:
            context += f"- {detail}\n"

    # Conversation details (new category)
    if 'conversation_details' in game_state['narrative_memory'] and game_state['narrative_memory'][
        'conversation_details']:
        context += "Conversation details:\n"
        for detail in game_state['narrative_memory']['conversation_details']:
            context += f"- {detail}\n"

    # Add relevant world facts
    context += "\nWorld knowledge:\n"
    for fact in game_state['world_facts']:
        context += f"- {fact}\n"

    # Add recent conversation history - increased from 6 to 8 for better context
    context += "\nRecent conversation:\n"
    all_exchanges = []
    for session in game_state['conversation_history']:
        all_exchanges.extend(session['exchanges'])

    # Get the most recent exchanges but limit to max_history
    recent_exchanges = all_exchanges[-max_history:] if len(all_exchanges) > max_history else all_exchanges
    for exchange in recent_exchanges:
        context += f"{exchange['speaker']}: {exchange['text']}\n"

    return context


@lru_cache(maxsize=50)
def get_cached_response(context_hash, player_input):
    """Get a cached response if available"""
    key = (context_hash, player_input)
    return response_cache.get(key)


def cache_response(context_hash, player_input, response):
    """Cache a response for future use"""
    key = (context_hash, player_input)
    response_cache[key] = response


def optimize_memory_updates(game_state, player_input, dm_response, model, plot_pace="Balanced"):
    """A more efficient memory extraction system that reduces processing time"""
    # Only update memory after X number of exchanges to reduce processing overhead
    if len(game_state['conversation_history'][-1]['exchanges']) % 3 != 0:  # Only process every 3rd exchange
        return {}, []

    # Create a simpler prompt for memory extraction
    simple_prompt = f"""
    Based on this exchange:
    Player: {player_input}
    DM: {dm_response}

    Extract 1-2 key points about:
    - Character development
    - Relationships
    - Plot developments
    - Environment details

    Format as bullet points.
    """

    # Get memory updates with a shorter, more focused prompt
    try:
        memory_prompt = ChatPromptTemplate.from_template(simple_prompt)
        memory_chain = memory_prompt | model
        memory_response = memory_chain.invoke({})

        # Simple parser for bullet points
        updates = {
            "world_facts": [],
            "character_development": [],
            "relationships": [],
            "plot_developments": [],
            "player_decisions": [],
            "environment_details": [],
            "conversation_details": []
        }

        # Basic parsing - much faster than regex
        for line in memory_response.split('\n'):
            line = line.strip()
            if not line:
                continue

            if "character" in line.lower() or "develop" in line.lower():
                updates["character_development"].append(line.replace('-', '').strip())
            elif "relation" in line.lower():
                updates["relationships"].append(line.replace('-', '').strip())
            elif "plot" in line.lower():
                updates["plot_developments"].append(line.replace('-', '').strip())
            elif "environ" in line.lower() or "location" in line.lower():
                updates["environment_details"].append(line.replace('-', '').strip())

        # Identify important updates - drastically simplified
        important_updates = []
        for category in ["plot_developments", "character_development"]:
            for item in updates.get(category, []):
                if "major" in item.lower() or "significant" in item.lower():
                    important_updates.append(f"{category.replace('_', ' ').title()}: {item}")

        return updates, important_updates

    except Exception as e:
        print(f"Error extracting memory: {e}")
        return {}, []


def update_dynamic_elements(game_state, memory_updates):
    """Updates game state with new elements the AI has created"""
    # Extract potential new NPCs from memory updates
    for category in ['character_development', 'relationships', 'plot_developments']:
        for item in memory_updates.get(category, []):
            # Look for patterns that suggest new NPCs
            npc_match = re.search(r"(?:new character|new npc):\s*([A-Z][a-z]+)", item, re.IGNORECASE)
            if npc_match:
                npc_name = npc_match.group(1).strip()
                # Check if this NPC already exists
                npc_exists = False
                for npc_id in game_state['npcs']:
                    if game_state['npcs'][npc_id]['name'].lower() == npc_name.lower():
                        npc_exists = True
                        break

                # Create new NPC if they don't exist
                if not npc_exists:
                    npc_id = "npc_" + "".join([c.lower() if c.isalnum() else "_" for c in npc_name])
                    # Extract additional details if available
                    race = "Unknown"
                    race_match = re.search(r"(?:a|an)\s+([a-z]+)\s+(?:man|woman|person|being)", item, re.IGNORECASE)
                    if race_match:
                        race = race_match.group(1).capitalize()

                    # Create basic NPC entry
                    game_state['npcs'][npc_id] = {
                        "name": npc_name,
                        "race": race,
                        "description": "A character recently introduced to the story.",
                        "location": game_state['game_info']['current_location'],
                        "disposition": "neutral",
                        "motivation": "unknown",
                        "knowledge": [],
                        "relationships": {},
                        "dialogue_style": "speaks normally"
                    }

                    # Add NPC to current location
                    current_loc = game_state['game_info']['current_location']
                    if npc_id not in game_state['locations'][current_loc]['npcs_present']:
                        game_state['locations'][current_loc]['npcs_present'].append(npc_id)

    # Extract potential new locations from memory updates
    for category in ['world_facts', 'plot_developments', 'environment_details']:
        for item in memory_updates.get(category, []):
            # Look for patterns that suggest new locations
            location_match = re.search(
                r"(?:new location|new place|discover[ed]*)\s*(?:called)?\s*(?:the)?\s*([A-Z][a-z\s]+)", item,
                re.IGNORECASE)
            if location_match:
                location_name = location_match.group(1).strip()
                # Check if this location already exists
                location_exists = False
                for loc_id in game_state['locations']:
                    if game_state['locations'][loc_id]['name'].lower() == location_name.lower():
                        location_exists = True
                        break

                # Create new location if it doesn't exist
                if not location_exists:
                    loc_id = "location_" + "".join([c.lower() if c.isalnum() else "_" for c in location_name])
                    # Get current location to create connection
                    current_loc = game_state['game_info']['current_location']

                    # Create basic location entry
                    game_state['locations'][loc_id] = {
                        "name": location_name,
                        "description": "A place recently discovered in the story.",
                        "ambience": "The atmosphere is yet to be fully experienced.",
                        "connected_to": [current_loc],
                        "npcs_present": [],
                        "points_of_interest": [],
                        "secrets": [],
                        "available_quests": [],
                        "visited": False
                    }

                    # Add connection from current location to new location
                    if loc_id not in game_state['locations'][current_loc]['connected_to']:
                        game_state['locations'][current_loc]['connected_to'].append(loc_id)

    return game_state


def generate_story_summary(game_state, model):
    """Generate a narrative summary of the story so far"""

    # Gather key story elements
    plot_developments = game_state['narrative_memory'].get('plot_developments', [])
    character_developments = game_state['narrative_memory'].get('character_development', [])
    world_facts = game_state['narrative_memory'].get('world_facts', [])
    relationships = game_state['narrative_memory'].get('relationships', [])
    player_decisions = game_state['narrative_memory'].get('player_decisions', [])

    # Get character name
    pc_id = list(game_state['player_characters'].keys())[0]
    pc_name = game_state['player_characters'][pc_id]['name']

    # Create prompt for summary generation
    summary_prompt = f"""
    Create a narrative summary of the following story elements as if recounting a tale. 
    Write in the style of a storyteller, focusing on events that have unfolded so far.
    Use 3-5 paragraphs total. Bold particularly important events or revelations.

    Character name: {pc_name}
    World: {game_state['game_info']['world_name']}

    Plot Developments:
    {' '.join(plot_developments)}

    Character Developments:
    {' '.join(character_developments)}

    World Details:
    {' '.join(world_facts)}

    Relationships:
    {' '.join(relationships)}

    Player Decisions:
    {' '.join(player_decisions)}

    Current location: {game_state['locations'][game_state['game_info']['current_location']]['name']}

    Current quest: {game_state['quests'].get(game_state['game_info']['current_quest'], {}).get('name', 'Unknown')}

    Write a story summary in past tense, as if recounting the adventures so far. Bold important events.
    Begin with 'The tale of [Character Name] in [World]...' and end with where the character currently stands.
    """

    # Create a simple prompt template
    summary_template = ChatPromptTemplate.from_template(summary_prompt)
    summary_chain = summary_template | model

    # Generate the summary
    try:
        narrative_summary = summary_chain.invoke({})

        # Process the summary to handle bold formatting
        processed_summary = narrative_summary.replace("**", "")  # Remove markdown bold for now

        return processed_summary
    except Exception as e:
        # Fallback if AI summary generation fails
        fallback_summary = [
            f"The tale of {pc_name} in {game_state['game_info']['world_name']} began with a quest for "
            f"{game_state['quests'].get(game_state['game_info']['current_quest'], {}).get('name', 'adventure')}."
        ]

        # Add some plot developments if available
        if plot_developments:
            fallback_summary.append("\nAlong the way, " + " Then ".join(plot_developments[-3:]) + ".")

        # Add current situation
        current_loc = game_state['locations'][game_state['game_info']['current_location']]['name']
        fallback_summary.append(f"\nCurrently, {pc_name} is at {current_loc}.")

        return "\n".join(fallback_summary)


class StreamingTextDisplay(QTextEdit):
    """Widget for displaying streaming text with typewriter effect"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(300)
        self.system_format = QTextCharFormat()
        self.system_format.setForeground(QColor(SYSTEM_COLOR))
        self.dm_name_format = QTextCharFormat()
        self.dm_name_format.setForeground(QColor(DM_NAME_COLOR))
        self.dm_text_format = QTextCharFormat()
        self.dm_text_format.setForeground(QColor(DM_TEXT_COLOR))
        self.player_format = QTextCharFormat()
        self.player_format.setForeground(QColor(PLAYER_COLOR))

    def append_system_message(self, text):
        """Add a system message with green text"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", self.system_format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_dm_message(self, text):
        """Add a DM message with cyan text"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("DM: ", self.dm_name_format)
        cursor.insertText(text + "\n", self.dm_text_format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_player_message(self, text):
        """Add a player message with amber text"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("You: ", self.player_format)
        cursor.insertText(text + "\n", self.player_format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def stream_text(self, text, format_type):
        """Stream text with the specified format"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if format_type == "system":
            cursor.insertText(text, self.system_format)
        elif format_type == "dm_name":
            cursor.insertText(text, self.dm_name_format)
        elif format_type == "dm_text":
            cursor.insertText(text, self.dm_text_format)
        elif format_type == "player":
            cursor.insertText(text, self.player_format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class ModelGenerationThread(QThread):
    """Thread for generating text from the model to prevent UI freezing"""

    # Signal emitted when new text is generated
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(str)

    def __init__(self, model, prompt_vars):
        super().__init__()
        self.model = model
        self.prompt_vars = prompt_vars
        self.full_response = ""

    def run(self):
        """Run the model generation"""
        try:
            prompt = ChatPromptTemplate.from_template(dm_template)
            chain = prompt | self.model

            # Stream the response token by token
            for chunk in chain.stream(self.prompt_vars):
                # Extract text from chunk (handling different possible formats)
                try:
                    if hasattr(chunk, 'content'):
                        chunk_text = str(chunk.content)
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        chunk_text = str(chunk['content'])
                    else:
                        chunk_text = str(chunk)

                    # Emit the generated text and add to full response
                    self.text_generated.emit(chunk_text)
                    self.full_response += chunk_text
                except Exception as e:
                    pass  # Skip any problematic chunks

        except Exception as e:
            # Fall back to standard generation if streaming fails
            try:
                prompt = ChatPromptTemplate.from_template(dm_template)
                chain = prompt | self.model
                self.full_response = chain.invoke(self.prompt_vars)
                self.text_generated.emit(self.full_response)
            except Exception as e2:
                self.text_generated.emit(f"\nError generating response: {str(e2)}")

        # Signal that generation is complete
        self.generation_complete.emit(self.full_response)


class StoryCreationWizard(QWidget):
    """Wizard for creating a new story"""

    story_created = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 0
        self.pages = []  # Initialize pages BEFORE calling setup_ui
        self.player_input = {}
        self.npcs = []
        self.setup_ui()  # Call setup_ui after initializing the attributes

    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)

        # Create a stacked widget for the different wizard pages
        self.stacked_layout = QVBoxLayout()

        # Create the basic info page
        basic_info_widget = QWidget()
        basic_info_layout = QFormLayout(basic_info_widget)

        # Model selection
        self.model_combo = QComboBox()
        available_models = get_available_ollama_models()

        if not available_models:
            available_models = ["No models found"]

        self.model_combo.addItems(available_models)
        basic_info_layout.addRow("AI Model:", self.model_combo)

        # Add Download Model button
        self.download_model_button = QPushButton("Download New Model")
        self.download_model_button.clicked.connect(self.show_model_download_dialog)
        basic_info_layout.addRow("", self.download_model_button)

        # Story title
        self.title_input = QLineEdit()
        basic_info_layout.addRow("Story Title:", self.title_input)

        # World name
        self.world_input = QLineEdit()
        basic_info_layout.addRow("World Name:", self.world_input)

        # Genre
        self.genre_input = QLineEdit()
        basic_info_layout.addRow("Genre:", self.genre_input)

        # Setting
        self.setting_input = QTextEdit()
        self.setting_input.setMaximumHeight(100)
        basic_info_layout.addRow("Setting Description:", self.setting_input)

        # Tone
        self.tone_input = QLineEdit()
        basic_info_layout.addRow("Tone:", self.tone_input)

        # Content rating
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["E - Family Friendly", "T - Teen", "M - Mature"])
        basic_info_layout.addRow("Content Rating:", self.rating_combo)

        # Plot pacing
        self.pacing_combo = QComboBox()
        self.pacing_combo.addItems(["Fast-paced", "Balanced", "Slice-of-life"])
        basic_info_layout.addRow("Plot Pacing:", self.pacing_combo)

        # Add the basic info page to the wizard
        self.stacked_layout.addWidget(basic_info_widget)
        self.pages.append(basic_info_widget)

        # Create the character page
        character_widget = QWidget()
        character_layout = QFormLayout(character_widget)

        # Character name
        self.character_name_input = QLineEdit()
        character_layout.addRow("Character Name:", self.character_name_input)

        # Character race
        self.character_race_input = QLineEdit()
        character_layout.addRow("Character Race:", self.character_race_input)

        # Character class
        self.character_class_input = QLineEdit()
        character_layout.addRow("Character Class:", self.character_class_input)

        # Character traits
        self.character_traits_input = QLineEdit()
        character_layout.addRow("Character Traits (comma separated):", self.character_traits_input)

        # Character abilities
        self.character_abilities_input = QLineEdit()
        character_layout.addRow("Character Abilities (comma separated):", self.character_abilities_input)

        # Add the character page to the wizard
        self.stacked_layout.addWidget(character_widget)
        self.pages.append(character_widget)

        # Create the location page
        location_widget = QWidget()
        location_layout = QFormLayout(location_widget)

        # Starting location name
        self.location_name_input = QLineEdit()
        location_layout.addRow("Starting Location Name:", self.location_name_input)

        # Starting location description
        self.location_desc_input = QTextEdit()
        self.location_desc_input.setMaximumHeight(100)
        location_layout.addRow("Starting Location Description:", self.location_desc_input)

        # Add the location page to the wizard
        self.stacked_layout.addWidget(location_widget)
        self.pages.append(location_widget)

        # Create the quest page
        quest_widget = QWidget()
        quest_layout = QFormLayout(quest_widget)

        # Quest name
        self.quest_name_input = QLineEdit()
        quest_layout.addRow("Initial Quest Name:", self.quest_name_input)

        # Quest description
        self.quest_desc_input = QTextEdit()
        self.quest_desc_input.setMaximumHeight(100)
        quest_layout.addRow("Initial Quest Description:", self.quest_desc_input)

        # World facts
        self.world_facts_input = QTextEdit()
        self.world_facts_input.setMaximumHeight(100)
        quest_layout.addRow("World Facts (one per line):", self.world_facts_input)

        # Add the quest page to the wizard
        self.stacked_layout.addWidget(quest_widget)
        self.pages.append(quest_widget)

        # Create the NPC page
        self.npc_widget = QWidget()
        npc_layout = QVBoxLayout(self.npc_widget)

        # NPCs list
        self.npcs_list = QListWidget()
        npc_layout.addWidget(QLabel("Added NPCs:"))
        npc_layout.addWidget(self.npcs_list)

        # NPC form
        npc_form = QGroupBox("Add NPC")
        npc_form_layout = QFormLayout(npc_form)

        # NPC name
        self.npc_name_input = QLineEdit()
        npc_form_layout.addRow("NPC Name:", self.npc_name_input)

        # NPC race
        self.npc_race_input = QLineEdit()
        npc_form_layout.addRow("NPC Race:", self.npc_race_input)

        # NPC description
        self.npc_desc_input = QTextEdit()
        self.npc_desc_input.setMaximumHeight(80)
        npc_form_layout.addRow("NPC Description:", self.npc_desc_input)

        # NPC disposition
        self.npc_disposition_input = QLineEdit()
        npc_form_layout.addRow("NPC Disposition:", self.npc_disposition_input)

        # NPC motivation
        self.npc_motivation_input = QLineEdit()
        npc_form_layout.addRow("NPC Motivation:", self.npc_motivation_input)

        # NPC dialogue style
        self.npc_dialogue_input = QLineEdit()
        npc_form_layout.addRow("NPC Dialogue Style:", self.npc_dialogue_input)

        # Add NPC button
        self.add_npc_button = QPushButton("Add NPC")
        self.add_npc_button.clicked.connect(self.add_npc)
        npc_form_layout.addRow("", self.add_npc_button)

        npc_layout.addWidget(npc_form)

        # Add the NPC page to the wizard
        self.stacked_layout.addWidget(self.npc_widget)
        self.pages.append(self.npc_widget)

        # Add the stacked layout to the main layout
        layout.addLayout(self.stacked_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.go_next)

        self.create_button = QPushButton("Create Story")
        self.create_button.clicked.connect(self.create_story)
        self.create_button.setVisible(False)

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.create_button)

        layout.addLayout(nav_layout)

        # Show the first page
        self.pages[self.current_page].setVisible(True)

    def show_model_download_dialog(self):
        """Show a dialog to download a new model"""
        model_dialog = QDialog(self)
        model_dialog.setWindowTitle("Download Model")
        model_layout = QVBoxLayout(model_dialog)

        model_label = QLabel("Enter the name of the model to download:")
        model_layout.addWidget(model_label)

        model_input = QLineEdit()
        model_input.setPlaceholderText("e.g., mistral-small, llama3, gemma")
        model_layout.addWidget(model_input)

        recommended_label = QLabel("Recommended models: mistral-small, llama3, gemma")
        model_layout.addWidget(recommended_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(model_dialog.accept)
        button_box.rejected.connect(model_dialog.reject)
        model_layout.addWidget(button_box)

        if model_dialog.exec() == QDialog.DialogCode.Accepted and model_input.text().strip():
            # Call the download model function from main window
            self.parent().download_model(model_input.text().strip())

            # Refresh model list
            self.model_combo.clear()
            available_models = get_available_ollama_models()
            if not available_models:
                available_models = ["No models found"]
            self.model_combo.addItems(available_models)

    def go_back(self):
        """Go to the previous page"""
        if self.current_page > 0:
            self.pages[self.current_page].setVisible(False)
            self.current_page -= 1
            self.pages[self.current_page].setVisible(True)

            # Update button states
            self.back_button.setEnabled(self.current_page > 0)
            self.next_button.setVisible(True)
            self.next_button.setEnabled(True)
            self.create_button.setVisible(False)

    def go_next(self):
        """Go to the next page"""
        if self.current_page < len(self.pages) - 1:
            self.pages[self.current_page].setVisible(False)
            self.current_page += 1
            self.pages[self.current_page].setVisible(True)

            # Update button states
            self.back_button.setEnabled(True)

            # If on the last page, show the create button instead of next
            if self.current_page == len(self.pages) - 1:
                self.next_button.setVisible(False)
                self.create_button.setVisible(True)

    def add_npc(self):
        """Add an NPC to the list"""
        npc = {
            "name": self.npc_name_input.text(),
            "race": self.npc_race_input.text(),
            "description": self.npc_desc_input.toPlainText(),
            "disposition": self.npc_disposition_input.text(),
            "motivation": self.npc_motivation_input.text(),
            "dialogue_style": self.npc_dialogue_input.text()
        }

        # Only add if the name is not empty
        if npc["name"]:
            self.npcs.append(npc)
            self.npcs_list.addItem(npc["name"])

            # Clear the form
            self.npc_name_input.clear()
            self.npc_race_input.clear()
            self.npc_desc_input.clear()
            self.npc_disposition_input.clear()
            self.npc_motivation_input.clear()
            self.npc_dialogue_input.clear()

    def create_story(self):
        """Create the story and emit the signal"""
        # Basic info
        self.player_input["model_name"] = self.model_combo.currentText()
        self.player_input["story_title"] = self.title_input.text()
        self.player_input["world_name"] = self.world_input.text()
        self.player_input["genre"] = self.genre_input.text()
        self.player_input["setting"] = self.setting_input.toPlainText()
        self.player_input["tone"] = self.tone_input.text()

        # Content rating
        rating_text = self.rating_combo.currentText()
        if "E" in rating_text:
            self.player_input["rating"] = "E"
        elif "T" in rating_text:
            self.player_input["rating"] = "T"
        elif "M" in rating_text:
            self.player_input["rating"] = "M"

        # Plot pacing
        self.player_input["plot_pace"] = self.pacing_combo.currentText()

        # Character info
        self.player_input["character_name"] = self.character_name_input.text()
        self.player_input["character_race"] = self.character_race_input.text()
        self.player_input["character_class"] = self.character_class_input.text()

        # Character traits
        if self.character_traits_input.text():
            self.player_input["character_traits"] = [t.strip() for t in self.character_traits_input.text().split(",")]

        # Character abilities
        if self.character_abilities_input.text():
            self.player_input["abilities"] = [a.strip() for a in self.character_abilities_input.text().split(",")]

        # Location info
        self.player_input["starting_location_name"] = self.location_name_input.text()
        self.player_input["starting_location_description"] = self.location_desc_input.toPlainText()

        # Quest info
        self.player_input["quest_name"] = self.quest_name_input.text()
        self.player_input["quest_description"] = self.quest_desc_input.toPlainText()

        # World facts
        if self.world_facts_input.toPlainText():
            self.player_input["world_facts"] = [f.strip() for f in self.world_facts_input.toPlainText().split("\n") if
                                                f.strip()]

        # NPCs
        if self.npcs:
            self.player_input["npcs"] = self.npcs

        # Emit the signal
        self.story_created.emit(self.player_input)


class SummaryWorker(QObject):
    """Worker for generating a story summary in a separate thread"""

    summary_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, game_state, model):
        super().__init__()
        self.game_state = game_state
        self.model = model

    def generate_summary(self):
        """Generate a summary of the story so far"""
        try:
            summary = generate_story_summary(self.game_state, self.model)
            self.summary_ready.emit(summary)
        except Exception as e:
            self.summary_ready.emit(f"Error generating summary: {str(e)}")
        finally:
            self.finished.emit()


class LaceAIdventureGUI(QMainWindow):
    """Main window for the adventure game"""

    def __init__(self):
        super().__init__()
        self.game_state = None
        self.story_name = None
        self.model = None

        # Check if Ollama is installed before setting up the UI
        self.check_ollama_installation()

    def check_ollama_installation(self):
        """Check if Ollama is installed and offer to install if not"""
        if not self.is_ollama_installed():
            reply = QMessageBox.question(self,
                                         "Ollama Not Found",
                                         "Ollama is required to run Lace's AIdventure Game but was not found on your system. Would you like to install it now?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.install_ollama()
            else:
                QMessageBox.warning(self, "Required Component Missing",
                                    "Ollama is required to run this application. The game may not function properly.")
                # Continue anyway and set up the UI
                self.setup_ui()
        else:
            # Ollama is installed, check if default model is available
            self.setup_ui()
            self.check_default_model()

    def is_ollama_installed(self):
        """Check if Ollama is installed on the system"""
        try:
            result = subprocess.run(['ollama', 'list'],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
            return result.returncode == 0
        except:
            return False

    def install_ollama(self):
        """Install Ollama on the user's system"""
        # Create progress dialog
        progress = QProgressDialog("Installing Ollama...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Installing Ollama")
        progress.setModal(True)
        progress.setCancelButton(None)  # No cancel button
        progress.setMinimumDuration(0)
        progress.setRange(0, 0)  # Indeterminate progress
        progress.setAutoClose(False)
        progress.show()

        # Start installation thread
        self.installer_thread = OllamaInstallerThread()
        self.installer_thread.progress_update.connect(progress.setLabelText)
        self.installer_thread.installation_complete.connect(
            lambda success, message: self.handle_installation_complete(success, message, progress))
        self.installer_thread.start()

    def handle_installation_complete(self, success, message, progress_dialog):
        """Handle the completion of Ollama installation"""
        progress_dialog.close()

        if success:
            QMessageBox.information(self, "Installation Complete", message)
            self.setup_ui()
            self.check_default_model()
        else:
            QMessageBox.warning(self, "Installation Failed",
                                f"{message}\n\nPlease try installing Ollama manually from https://ollama.com/")
            self.setup_ui()

    def check_default_model(self):
        """Check if a default model is available"""
        # Try to find an available model
        available_models = get_available_ollama_models()

        if not available_models:
            reply = QMessageBox.question(self,
                                         "No Models Found",
                                         "No Ollama models were found on your system. Would you like to download the recommended model (mistral-small)?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.download_model("mistral-small")

    def download_model(self, model_name):
        """Download an Ollama model"""
        # Create progress dialog
        progress = QProgressDialog(f"Downloading {model_name}...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Downloading Model")
        progress.setModal(True)
        progress.setCancelButton(None)  # No cancel button
        progress.setMinimumDuration(0)
        progress.setRange(0, 0)  # Indeterminate progress
        progress.setAutoClose(False)
        progress.show()

        # Start download thread
        self.downloader_thread = ModelDownloaderThread(model_name)
        self.downloader_thread.progress_update.connect(progress.setLabelText)
        self.downloader_thread.download_complete.connect(
            lambda success, message: self.handle_download_complete(success, message, progress))
        self.downloader_thread.start()

    def handle_download_complete(self, success, message, progress_dialog):
        """Handle the completion of model download"""
        progress_dialog.close()

        if success:
            QMessageBox.information(self, "Download Complete", message)
        else:
            QMessageBox.warning(self, "Download Failed",
                                f"{message}\n\nYou may need to download models manually using 'ollama pull model-name'")

    def setup_ui(self):
        """Set up the main UI components"""
        self.setWindowTitle("Lace's AIdventure Game")
        self.setMinimumSize(900, 700)

        # Create the central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget for different screens
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Create the game tabs
        self.main_menu_tab = self.create_main_menu_tab()
        self.game_tab = self.create_game_tab()
        self.story_creation_tab = self.create_story_creation_tab()
        self.story_management_tab = self.create_story_management_tab()

        # Add the tabs to the tab widget
        self.tabs.addTab(self.main_menu_tab, "Main Menu")
        self.tabs.addTab(self.game_tab, "Game")
        self.tabs.addTab(self.story_creation_tab, "Create Story")
        self.tabs.addTab(self.story_management_tab, "Manage Stories")

        # Add the tab widget to the main layout
        main_layout.addWidget(self.tabs)

        # Start with the main menu and hide other tabs
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabVisible(1, False)  # Hide game tab initially
        self.tabs.setTabVisible(2, False)  # Hide story creation tab initially
        self.tabs.setTabVisible(3, False)  # Hide story management tab initially

    def create_main_menu_tab(self):
        """Create the main menu interface"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Add title label
        title_label = QLabel("Lace's AIdventure Game")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Add a subtitle
        subtitle_label = QLabel("Interactive AI-Powered Text Adventures")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(16)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)

        # Add some spacing
        layout.addSpacing(40)

        # Create a container for the buttons with fixed width
        button_container = QWidget()
        button_container.setFixedWidth(300)
        button_layout = QVBoxLayout(button_container)

        # Add buttons for main menu options
        new_story_button = QPushButton("Create New Story")
        new_story_button.setMinimumHeight(50)
        load_story_button = QPushButton("Load Existing Story")
        load_story_button.setMinimumHeight(50)
        manage_stories_button = QPushButton("Manage Stories")
        manage_stories_button.setMinimumHeight(50)
        exit_button = QPushButton("Exit")
        exit_button.setMinimumHeight(50)

        # Connect signals to slots
        new_story_button.clicked.connect(self.show_story_creation)
        load_story_button.clicked.connect(self.show_story_load)
        manage_stories_button.clicked.connect(self.show_story_management)
        exit_button.clicked.connect(self.close)

        # Add buttons to layout
        button_layout.addWidget(new_story_button)
        button_layout.addWidget(load_story_button)
        button_layout.addWidget(manage_stories_button)
        button_layout.addWidget(exit_button)
        button_layout.addStretch()

        # Center the button container
        layout.addWidget(button_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return tab

    def create_game_tab(self):
        """Create the game interface"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create the game display panel
        game_panel = QWidget()
        game_layout = QVBoxLayout(game_panel)

        # Create the text display area
        self.text_display = StreamingTextDisplay()
        game_layout.addWidget(self.text_display)

        # Create the input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter your command...")
        self.input_field.returnPressed.connect(self.process_input)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.process_input)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        game_layout.addLayout(input_layout)

        # Create the command buttons
        cmd_layout = QHBoxLayout()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_game)

        self.memory_button = QPushButton("Memory")
        self.memory_button.clicked.connect(self.show_memory)

        self.summary_button = QPushButton("Summary")
        self.summary_button.clicked.connect(self.show_summary)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.quit_game)

        cmd_layout.addWidget(self.save_button)
        cmd_layout.addWidget(self.memory_button)
        cmd_layout.addWidget(self.summary_button)
        cmd_layout.addWidget(self.quit_button)

        game_layout.addLayout(cmd_layout)

        # Create the game status panel
        status_panel = QScrollArea()
        status_panel.setWidgetResizable(True)
        status_panel.setMinimumWidth(250)
        status_panel.setMaximumWidth(300)

        status_content = QWidget()
        self.status_layout = QVBoxLayout(status_content)

        # Game info section
        game_info_group = QGroupBox("Game Info")
        game_info_layout = QVBoxLayout(game_info_group)
        self.game_title_label = QLabel("Title: ")
        self.game_world_label = QLabel("World: ")
        self.game_location_label = QLabel("Location: ")
        game_info_layout.addWidget(self.game_title_label)
        game_info_layout.addWidget(self.game_world_label)
        game_info_layout.addWidget(self.game_location_label)

        # Character info section
        character_info_group = QGroupBox("Character")
        character_info_layout = QVBoxLayout(character_info_group)
        self.character_name_label = QLabel("Name: ")
        self.character_class_label = QLabel("Class: ")
        self.character_race_label = QLabel("Race: ")
        self.character_health_label = QLabel("Health: ")
        character_info_layout.addWidget(self.character_name_label)
        character_info_layout.addWidget(self.character_class_label)
        character_info_layout.addWidget(self.character_race_label)
        character_info_layout.addWidget(self.character_health_label)

        # Quest info section
        quest_info_group = QGroupBox("Current Quest")
        quest_info_layout = QVBoxLayout(quest_info_group)
        self.quest_name_label = QLabel("Name: ")
        self.quest_desc_label = QLabel("Description: ")
        self.quest_desc_label.setWordWrap(True)
        quest_info_layout.addWidget(self.quest_name_label)
        quest_info_layout.addWidget(self.quest_desc_label)

        # NPCs section
        npcs_group = QGroupBox("NPCs Present")
        npcs_layout = QVBoxLayout(npcs_group)
        self.npcs_list = QListWidget()
        npcs_layout.addWidget(self.npcs_list)

        # Add all sections to the status layout
        self.status_layout.addWidget(game_info_group)
        self.status_layout.addWidget(character_info_group)
        self.status_layout.addWidget(quest_info_group)
        self.status_layout.addWidget(npcs_group)
        self.status_layout.addStretch()

        status_panel.setWidget(status_content)

        # Add the panels to the splitter
        splitter.addWidget(game_panel)
        splitter.addWidget(status_panel)

        # Set the initial sizes
        splitter.setSizes([600, 300])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def create_story_creation_tab(self):
        """Create the story creation interface"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create the story creation wizard
        self.story_wizard = StoryCreationWizard(self)
        self.story_wizard.story_created.connect(self.create_new_story)

        layout.addWidget(self.story_wizard)

        return tab

    def create_story_management_tab(self):
        """Create the story management interface"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Add title
        title_label = QLabel("Manage Stories")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Create a list widget for the stories
        self.stories_list = QListWidget()
        layout.addWidget(self.stories_list)

        # Create buttons for actions
        button_layout = QHBoxLayout()

        self.load_story_button = QPushButton("Load Selected Story")
        self.load_story_button.clicked.connect(self.load_selected_story)

        self.delete_story_button = QPushButton("Delete Selected Story")
        self.delete_story_button.clicked.connect(self.delete_selected_story)

        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self.refresh_stories_list)

        button_layout.addWidget(self.load_story_button)
        button_layout.addWidget(self.delete_story_button)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        # Back button
        back_button = QPushButton("Back to Main Menu")
        back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        layout.addWidget(back_button)

        return tab

    def show_story_creation(self):
        """Show the story creation tab"""
        self.tabs.setTabVisible(2, True)
        self.tabs.setCurrentIndex(2)

    def show_story_load(self):
        """Show the story load interface"""
        self.refresh_stories_list()
        self.tabs.setTabVisible(3, True)
        self.tabs.setCurrentIndex(3)

    def show_story_management(self):
        """Show the story management tab"""
        self.refresh_stories_list()
        self.tabs.setTabVisible(3, True)
        self.tabs.setCurrentIndex(3)

    def refresh_stories_list(self):
        """Refresh the list of stories"""
        self.stories_list.clear()
        stories = list_stories()

        for file_name, story_title in stories:
            self.stories_list.addItem(f"{story_title} [{file_name}]")

    def load_selected_story(self):
        """Load the selected story"""
        selected_items = self.stories_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Story Selected", "Please select a story to load.")
            return

        selected_item = selected_items[0]
        text = selected_item.text()

        # Extract the file name from the text
        match = re.search(r"\[(.*?)\]", text)
        if match:
            file_name = match.group(1)
            self.load_story(file_name)
        else:
            QMessageBox.warning(self, "Invalid Story", "Could not parse the story file name.")

    def delete_selected_story(self):
        """Delete the selected story"""
        selected_items = self.stories_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Story Selected", "Please select a story to delete.")
            return

        selected_item = selected_items[0]
        text = selected_item.text()

        # Extract the file name and title from the text
        match = re.search(r"(.*?) \[(.*?)\]", text)
        if match:
            story_title = match.group(1)
            file_name = match.group(2)

            # Confirm deletion
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete '{story_title}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if delete_story(file_name):
                    QMessageBox.information(self, "Success", f"Story '{story_title}' deleted successfully.")
                    self.refresh_stories_list()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete story '{story_title}'.")
        else:
            QMessageBox.warning(self, "Invalid Story", "Could not parse the story information.")

    def create_new_story(self, player_input):
        """Create a new story from the wizard input"""
        # Initialize the game state
        self.game_state = init_game_state(player_input)
        self.story_name = player_input["story_title"]

        # Initialize the model
        self.model = get_faster_model(self.game_state["game_info"]["model_name"])

        # Generate initial context
        context = generate_context(self.game_state)
        initial_prompt = "Please provide a brief introduction to this world and the beginning of my adventure."

        # Setup prompt variables for streaming
        prompt_vars = {
            'genre': self.game_state['game_info']['genre'],
            'world_name': self.game_state['game_info']['world_name'],
            'setting_description': self.game_state['game_info']['setting'],
            'tone': self.game_state['game_info']['tone'],
            'rating': self.game_state['game_info']['rating'],
            'plot_pace': self.game_state['game_info']['plot_pace'],
            'context': context,
            'question': initial_prompt
        }

        # Clear the text display
        self.text_display.clear()

        # Add a system message
        self.text_display.append_system_message("Creating your world...")

        # Start the generation thread
        self.generation_thread = ModelGenerationThread(self.model, prompt_vars)
        self.generation_thread.text_generated.connect(lambda text: self.text_display.stream_text(text, "dm_text"))
        self.generation_thread.generation_complete.connect(
            lambda response: self.handle_initial_response(initial_prompt, response))
        self.generation_thread.start()

        # Show the game tab
        self.tabs.setTabVisible(1, True)
        self.tabs.setCurrentIndex(1)

        # Update the game status panel
        self.update_game_status()

    def handle_initial_response(self, initial_prompt, response):
        """Handle the initial response from the model"""
        # Add the initial prompt and response to conversation history
        self.game_state['conversation_history'][0]['exchanges'].append({
            "speaker": "Player",
            "text": initial_prompt
        })
        self.game_state['conversation_history'][0]['exchanges'].append({
            "speaker": "DM",
            "text": response
        })

        # Add initial narrative memory
        initial_memory, _ = optimize_memory_updates(
            self.game_state,
            initial_prompt,
            response,
            self.model,
            self.game_state['game_info']['plot_pace']
        )

        # Update memory
        for category, items in initial_memory.items():
            if category not in self.game_state['narrative_memory']:
                self.game_state['narrative_memory'][category] = []
            self.game_state['narrative_memory'][category].extend(items)

        # Save the initial game state
        save_game_state(self.game_state, self.story_name)

        # Enable the input field
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

    def load_story(self, file_name):
        """Load a story from a file"""
        # Load the game state
        self.game_state = load_game_state(file_name)

        if not self.game_state:
            QMessageBox.warning(self, "Error", "Failed to load the story. The save file might be corrupted.")
            return

        self.story_name = self.game_state['game_info']['title']

        # Initialize the model
        model_name = self.game_state["game_info"].get("model_name", "mistral-small")
        self.model = get_faster_model(model_name)

        # Check if plot pacing exists, add if not (for backwards compatibility)
        if 'plot_pace' not in self.game_state['game_info']:
            pace_dialog = QDialog(self)
            pace_dialog.setWindowTitle("Select Plot Pacing")
            pace_layout = QVBoxLayout(pace_dialog)

            pace_label = QLabel("This story doesn't have plot pacing set. Please choose one:")
            pace_layout.addWidget(pace_label)

            pace_combo = QComboBox()
            pace_combo.addItems(["Fast-paced", "Balanced", "Slice-of-life"])
            pace_layout.addWidget(pace_combo)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(pace_dialog.accept)
            pace_layout.addWidget(button_box)

            if pace_dialog.exec() == QDialog.DialogCode.Accepted:
                self.game_state['game_info']['plot_pace'] = pace_combo.currentText()

        # Check if rating exists, add if not (for backwards compatibility)
        if 'rating' not in self.game_state['game_info']:
            rating_dialog = QDialog(self)
            rating_dialog.setWindowTitle("Select Content Rating")
            rating_layout = QVBoxLayout(rating_dialog)

            rating_label = QLabel("This story doesn't have a content rating set. Please choose one:")
            rating_layout.addWidget(rating_label)

            rating_combo = QComboBox()
            rating_combo.addItems(["E - Family Friendly", "T - Teen", "M - Mature"])
            rating_layout.addWidget(rating_combo)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(rating_dialog.accept)
            rating_layout.addWidget(button_box)

            if rating_dialog.exec() == QDialog.DialogCode.Accepted:
                rating_text = rating_combo.currentText()
                if "E" in rating_text:
                    self.game_state['game_info']['rating'] = "E"
                elif "T" in rating_text:
                    self.game_state['game_info']['rating'] = "T"
                elif "M" in rating_text:
                    self.game_state['game_info']['rating'] = "M"

        # Check if narrative memory exists, add if not (for backwards compatibility)
        if 'narrative_memory' not in self.game_state:
            self.game_state['narrative_memory'] = {
                "world_facts": [],
                "character_development": [],
                "relationships": [],
                "plot_developments": [],
                "player_decisions": [],
                "environment_details": [],
                "conversation_details": []
            }

            # Rebuild narrative memory from conversation history
            self.text_display.append_system_message("Rebuilding narrative memory from history...")

            all_exchanges = []
            for session in self.game_state['conversation_history']:
                all_exchanges.extend(session['exchanges'])

            # Process exchanges in pairs
            for i in range(0, len(all_exchanges), 2):
                if i + 1 < len(all_exchanges):
                    player_input = all_exchanges[i]['text']
                    dm_response = all_exchanges[i + 1]['text']

                    # Extract memory updates
                    memory_updates, _ = optimize_memory_updates(
                        self.game_state,
                        player_input,
                        dm_response,
                        self.model,
                        self.game_state['game_info'].get('plot_pace', 'Balanced')
                    )

                    # Add memory items
                    for category, items in memory_updates.items():
                        if category not in self.game_state['narrative_memory']:
                            self.game_state['narrative_memory'][category] = []
                        for item in items:
                            if item not in self.game_state['narrative_memory'][category]:
                                self.game_state['narrative_memory'][category].append(item)

        # Add environment_details and conversation_details if missing
        if 'environment_details' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['environment_details'] = []
        if 'conversation_details' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['conversation_details'] = []

        # Clear the text display
        self.text_display.clear()

        # Display the conversation history
        self.text_display.append_system_message(f"Loaded story: {self.story_name}")

        all_exchanges = []
        for session in self.game_state['conversation_history']:
            all_exchanges.extend(session['exchanges'])

        # Display the last few exchanges
        num_exchanges = min(10, len(all_exchanges))
        for i in range(len(all_exchanges) - num_exchanges, len(all_exchanges)):
            exchange = all_exchanges[i]
            if exchange['speaker'] == "Player":
                self.text_display.append_player_message(exchange['text'])
            else:
                self.text_display.append_dm_message(exchange['text'])

        # Update the game status panel
        self.update_game_status()

        # Show the game tab
        self.tabs.setTabVisible(1, True)
        self.tabs.setCurrentIndex(1)

        # Enable the input field
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

    def process_input(self):
        """Process the player input"""
        player_input = self.input_field.text().strip()

        if not player_input:
            return

        # Special commands
        if player_input.lower() in ['exit', 'quit']:
            self.quit_game()
            return

        if player_input.lower() == 'save':
            self.save_game()
            return

        if player_input.lower() == 'memory':
            self.show_memory()
            return

        if player_input.lower() == 'summary':
            self.show_summary()
            return

        # Display the player input
        self.text_display.append_player_message(player_input)

        # Clear the input field
        self.input_field.clear()

        # Disable the input field while generating response
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)

        # Generate context
        context = generate_context(self.game_state)

        # Calculate context hash for caching
        context_hash = hashlib.md5(context.encode()).hexdigest()

        # Check for cached response
        cached_response = get_cached_response(context_hash, player_input)
        if cached_response:
            self.text_display.append_dm_message(cached_response)
            self.update_game_state(player_input, cached_response)
            self.input_field.setEnabled(True)
            self.send_button.setEnabled(True)
            self.input_field.setFocus()
        else:
            # Setup prompt variables
            prompt_vars = {
                'genre': self.game_state['game_info']['genre'],
                'world_name': self.game_state['game_info']['world_name'],
                'setting_description': self.game_state['game_info']['setting'],
                'tone': self.game_state['game_info']['tone'],
                'rating': self.game_state['game_info']['rating'],
                'plot_pace': self.game_state['game_info'].get('plot_pace', 'Balanced'),
                'context': context,
                'question': player_input
            }

            # Start the generation thread
            self.text_display.stream_text("DM: ", "dm_name")

            self.generation_thread = ModelGenerationThread(self.model, prompt_vars)
            self.generation_thread.text_generated.connect(lambda text: self.text_display.stream_text(text, "dm_text"))
            self.generation_thread.generation_complete.connect(
                lambda response: self.finalize_response(player_input, response, context_hash))
            self.generation_thread.start()

    def finalize_response(self, player_input, response, context_hash):
        """Finalize the response from the model"""
        # Cache the response
        cache_response(context_hash, player_input, response)

        # Add a newline
        self.text_display.stream_text("\n", "dm_text")

        # Update the game state
        self.update_game_state(player_input, response)

        # Re-enable the input field
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

    def update_game_state(self, player_input, dm_response):
        """Update the game state based on player input and DM response"""
        # Add to conversation history
        current_session = self.game_state['game_info']['session_count']

        # Find current session or create new one
        session_found = False
        for session in self.game_state['conversation_history']:
            if session['session'] == current_session:
                session['exchanges'].append({"speaker": "Player", "text": player_input})
                session['exchanges'].append({"speaker": "DM", "text": dm_response})
                session_found = True
                break

        if not session_found:
            self.game_state['conversation_history'].append({
                "session": current_session,
                "exchanges": [
                    {"speaker": "Player", "text": player_input},
                    {"speaker": "DM", "text": dm_response}
                ]
            })

        # Get plot pacing preference
        plot_pace = self.game_state['game_info'].get('plot_pace', 'Balanced')

        # Update memory
        memory_updates, important_updates = optimize_memory_updates(
            self.game_state,
            player_input,
            dm_response,
            self.model,
            plot_pace
        )

        # Add new memory items without duplicates
        for category, items in memory_updates.items():
            if category not in self.game_state['narrative_memory']:
                self.game_state['narrative_memory'][category] = []

            for item in items:
                if item not in self.game_state['narrative_memory'][category]:
                    self.game_state['narrative_memory'][category].append(item)

        # Dynamic element creation from the main.py functions
        self.game_state = update_dynamic_elements(self.game_state, memory_updates)

        # Store important updates
        if important_updates:
            self.game_state['important_updates'] = important_updates

            # Display important updates
            self.text_display.append_system_message("! Important developments:")
            for update in important_updates:
                self.text_display.append_system_message(f"* {update}")

        # Save the game state
        save_game_state(self.game_state, self.story_name)

        # Update the game status panel
        self.update_game_status()

    def update_game_status(self):
        """Update the game status panel"""
        if not self.game_state:
            return

        # Update game info
        self.game_title_label.setText(f"Title: {self.game_state['game_info']['title']}")
        self.game_world_label.setText(f"World: {self.game_state['game_info']['world_name']}")

        current_loc_id = self.game_state['game_info']['current_location']
        self.game_location_label.setText(f"Location: {self.game_state['locations'][current_loc_id]['name']}")

        # Update character info
        pc_id = list(self.game_state['player_characters'].keys())[0]
        pc = self.game_state['player_characters'][pc_id]

        self.character_name_label.setText(f"Name: {pc['name']}")
        self.character_class_label.setText(f"Class: {pc['class']}")
        self.character_race_label.setText(f"Race: {pc['race']}")
        self.character_health_label.setText(f"Health: {pc['health']}/{pc['max_health']}")

        # Update quest info
        current_quest_id = self.game_state['game_info']['current_quest']
        if current_quest_id and current_quest_id in self.game_state['quests']:
            quest = self.game_state['quests'][current_quest_id]
            self.quest_name_label.setText(f"Name: {quest['name']}")
            self.quest_desc_label.setText(f"Description: {quest['description']}")

        # Update NPCs list
        self.npcs_list.clear()
        location = self.game_state['locations'][current_loc_id]
        for npc_id in location['npcs_present']:
            npc = self.game_state['npcs'][npc_id]
            self.npcs_list.addItem(f"{npc['name']} - {npc['disposition']}")

    def save_game(self):
        """Save the game"""
        if self.game_state and self.story_name:
            save_game_state(self.game_state, self.story_name)
            self.text_display.append_system_message("Game saved!")

    def show_memory(self):
        """Show the narrative memory"""
        if not self.game_state:
            return

        memory_dialog = QDialog(self)
        memory_dialog.setWindowTitle("Narrative Memory")
        memory_dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(memory_dialog)

        memory_text = QTextBrowser()
        memory_text.setOpenExternalLinks(False)

        # Add memory categories
        memory = self.game_state['narrative_memory']

        memory_html = "<h2>Narrative Memory</h2>"

        # World facts
        if memory['world_facts']:
            memory_html += "<h3>World Facts:</h3><ul>"
            for item in memory['world_facts']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Character development
        if memory['character_development']:
            memory_html += "<h3>Character Development:</h3><ul>"
            for item in memory['character_development']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Relationships
        if memory['relationships']:
            memory_html += "<h3>Relationships:</h3><ul>"
            for item in memory['relationships']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Plot developments
        if memory['plot_developments']:
            memory_html += "<h3>Plot Developments:</h3><ul>"
            for item in memory['plot_developments']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Player decisions
        if memory['player_decisions']:
            memory_html += "<h3>Important Player Decisions:</h3><ul>"
            for item in memory['player_decisions']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Environment details
        if memory.get('environment_details', []):
            memory_html += "<h3>Environment Details:</h3><ul>"
            for item in memory['environment_details']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        # Conversation details
        if memory.get('conversation_details', []):
            memory_html += "<h3>Conversation Details:</h3><ul>"
            for item in memory['conversation_details']:
                memory_html += f"<li>{item}</li>"
            memory_html += "</ul>"

        memory_text.setHtml(memory_html)
        layout.addWidget(memory_text)

        close_button = QPushButton("Close")
        close_button.clicked.connect(memory_dialog.accept)
        layout.addWidget(close_button)

        memory_dialog.exec()

    def show_summary(self):
        """Show a summary of the story so far"""
        if not self.game_state:
            return

        summary_dialog = QDialog(self)
        summary_dialog.setWindowTitle("Story Summary")
        summary_dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(summary_dialog)

        # Add a header
        header_label = QLabel("The Story So Far...")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Create a text display for the summary
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

        # Add a loading message
        self.summary_text.setPlainText("Generating summary...")

        # Create a thread to generate the summary
        self.summary_thread = QThread()
        self.summary_worker = SummaryWorker(self.game_state, self.model)
        self.summary_worker.moveToThread(self.summary_thread)

        self.summary_thread.started.connect(self.summary_worker.generate_summary)
        self.summary_worker.summary_ready.connect(self.display_summary)
        self.summary_worker.finished.connect(self.summary_thread.quit)

        # Start the thread
        self.summary_thread.start()

        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(summary_dialog.accept)
        layout.addWidget(close_button)

        # Show the dialog
        summary_dialog.exec()

    def display_summary(self, summary):
        """Display the generated summary"""
        self.summary_text.clear()

        # Split the summary into paragraphs
        paragraphs = summary.split("\n\n")

        # Add each paragraph
        for paragraph in paragraphs:
            # Check for bold markers
            if "**" in paragraph:
                parts = paragraph.split("**")
                for i, part in enumerate(parts):
                    if i % 2 == 0:  # Not bold
                        self.summary_text.insertPlainText(part)
                    else:  # Bold
                        format = QTextCharFormat()
                        format.setFontWeight(QFont.Weight.Bold)
                        cursor = self.summary_text.textCursor()
                        cursor.insertText(part, format)
                        self.summary_text.setTextCursor(cursor)
            else:
                self.summary_text.insertPlainText(paragraph)

            # Add a newline after each paragraph
            self.summary_text.insertPlainText("\n\n")

    def quit_game(self):
        """Quit the current game"""
        if self.game_state and self.story_name:
            # Save the game state
            save_game_state(self.game_state, self.story_name)

        # Reset the game state
        self.game_state = None
        self.story_name = None
        self.model = None

        # Hide the game tab
        self.tabs.setTabVisible(1, False)

        # Show the main menu
        self.tabs.setCurrentIndex(0)


def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)

    # Set app style
    app.setStyle("Fusion")

    window = LaceAIdventureGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()