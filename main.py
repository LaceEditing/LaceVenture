from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import subprocess
import json
import os
import glob
import sys
import re

# Directory for storing game stories
STORIES_DIR = "rpg_stories"
os.makedirs(STORIES_DIR, exist_ok=True)


# Terminal colors - fixed with Unicode escape sequences
class Colors:
    DM_NAME = '\u001b[1;36m'  # Cyan, bold
    DM_TEXT = '\u001b[0;36m'  # Cyan
    PLAYER = '\u001b[0;33m'  # Yellow
    SYSTEM = '\u001b[0;32m'  # Green
    RESET = '\u001b[0m'  # Reset to default


# Adjusted DM prompt template with content rating and plot pacing awareness
dm_template = """
You are an experienced Dungeon Master for a {genre} RPG set in {world_name}. Your role is to:

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
- GAMEPLAY: The player character should never speak on their own, unless the user tells them to in their responses. You will never generate dialogue from their perspective

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

# Enhanced memory update prompt with focus on details
memory_update_template = """
Based on the following exchange, extract important narrative information to remember:

Player: {player_input}
DM: {dm_response}

Current narrative memory:
{current_memory}

Plot pacing style: {plot_pace}

Extract NEW information about:
1. World facts (new locations, history, customs)
2. Character development (player or NPCs)
3. Relationships (how characters relate to each other)
4. Plot development (story progression)
5. Important decisions or actions taken
6. Environment details (room descriptions, objects, atmosphere, sensory details)
7. Conversation details (important dialogue, information shared, questions raised)

For "Fast-paced" stories, highlight all plot developments.
For "Balanced" stories, highlight only significant plot developments.
For "Slice-of-life" stories, highlight only major plot revelations or developments.

Format each piece as a brief, factual statement.
Return ONLY new information not already in the narrative memory.
Keep each entry concise (max 15 words).
If no new information was revealed, return "No new information to record."

New information to add to memory:
"""

# model_name = 'llama3'
# model = OllamaLLM(model=model_name)


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

        # For debugging
        print(f"Command output: {result.stdout}")
        print(f"Command error: {result.stderr}")

        # Both approaches failed, return default list
        return ["llama3", "mistral-small", "dolphin-mixtral", "gemma", "llama2"]

    except Exception as e:
        print(f"Error getting Ollama models: {e}")
        # Return some default models that are likely to be available
        return ["llama3", "mistral-small", "dolphin-mixtral", "gemma", "llama2"]

def colored_print(text, color, slow=False):
    """Print text with color, never using slow printing"""
    colored_text = f"{color}{text}{Colors.RESET}"
    print(colored_text)


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
    colored_print(f"Game saved to {file_path}", Colors.SYSTEM)


def load_game_state(story_name):
    """Load the game state from a JSON file"""
    file_path = get_story_path(story_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            colored_print(f"Error loading game state: {e}", Colors.SYSTEM)
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
            colored_print(f"Error deleting story: {e}", Colors.SYSTEM)
    return False


def generate_context(game_state, max_history=8):
    """Generate context string from game state for the LLM, with enhanced detail recall"""
    context = ""

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


def extract_memory_updates(player_input, dm_response, current_memory, model, plot_pace="Balanced"):
    """Extract memory updates from the exchange with improved detail capturing and plot pacing awareness"""
    memory_prompt = ChatPromptTemplate.from_template(memory_update_template)

    # Create a string representation of current memory
    memory_str = ""
    for category, items in current_memory.items():
        if items:
            memory_str += f"{category.replace('_', ' ').title()}:\n"
            for item in items:
                memory_str += f"- {item}\n"

    # Get memory updates
    try:
        memory_chain = memory_prompt | model
        memory_response = memory_chain.invoke({
            'player_input': player_input,
            'dm_response': dm_response,
            'current_memory': memory_str,
            'plot_pace': plot_pace
        })

        # Parse the response into categories
        updates = {
            "world_facts": [],
            "character_development": [],
            "relationships": [],
            "plot_developments": [],
            "player_decisions": [],
            "environment_details": [],
            "conversation_details": []
        }

        # Track important updates for player notification
        important_updates = []

        if "No new information to record" not in memory_response:
            # Extract categories with regex
            world_facts = re.findall(r"World facts?:?\s*(.+?)(?=Character|\n\n|Environment|Conversation|$)",
                                     memory_response, re.DOTALL)
            character_dev = re.findall(
                r"Character development:?\s*(.+?)(?=Relationship|\n\n|Environment|Conversation|$)", memory_response,
                re.DOTALL)
            relationships = re.findall(r"Relationships?:?\s*(.+?)(?=Plot|\n\n|Environment|Conversation|$)",
                                       memory_response, re.DOTALL)
            plot_dev = re.findall(r"Plot developments?:?\s*(.+?)(?=Player|\n\n|Environment|Conversation|$)",
                                  memory_response, re.DOTALL)
            decisions = re.findall(
                r"(?:Player decisions|Important decisions):?\s*(.+?)(?=\n\n|Environment|Conversation|$)",
                memory_response, re.DOTALL)
            environment = re.findall(r"Environment details:?\s*(.+?)(?=\n\n|Conversation|$)", memory_response,
                                     re.DOTALL)
            conversation = re.findall(r"Conversation details:?\s*(.+?)(?=\n\n|$)", memory_response, re.DOTALL)

            # Process world facts
            if world_facts:
                for item in world_facts[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["world_facts"].append(item)

            # Process character development
            if character_dev:
                for item in character_dev[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["character_development"].append(item)
                        # Character developments importance depends on plot pacing
                        if plot_pace == "Fast-paced":
                            if "significant" in item.lower() or "reveal" in item.lower() or "transform" in item.lower():
                                important_updates.append(f"Character: {item}")
                        elif plot_pace == "Balanced":
                            if "major" in item.lower() and ("revelation" in item.lower() or "change" in item.lower()):
                                important_updates.append(f"Character: {item}")
                        # For slice-of-life, rarely show character updates as notifications

            # Process relationships
            if relationships:
                for item in relationships[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["relationships"].append(item)
                        # Relationships are emphasized more in slice-of-life
                        if plot_pace == "Slice-of-life" and ("significant" in item.lower() or "major" in item.lower()):
                            important_updates.append(f"Relationship: {item}")

            # Process plot developments
            if plot_dev:
                for item in plot_dev[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["plot_developments"].append(item)
                        # Plot developments importance depends on pacing
                        if plot_pace == "Fast-paced":
                            # In fast-paced, show all plot developments
                            important_updates.append(f"Plot: {item}")
                        elif plot_pace == "Balanced":
                            # In balanced, show significant plot developments
                            if "significant" in item.lower() or "major" in item.lower() or "reveal" in item.lower():
                                important_updates.append(f"Plot: {item}")
                        elif plot_pace == "Slice-of-life":
                            # In slice-of-life, only show very major plot developments
                            if "major revelation" in item.lower() or "crucial" in item.lower():
                                important_updates.append(f"Plot: {item}")

            # Process player decisions
            if decisions:
                for item in decisions[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["player_decisions"].append(item)

            # Process environment details (new)
            if environment:
                for item in environment[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["environment_details"].append(item)

            # Process conversation details (new)
            if conversation:
                for item in conversation[0].strip().split('\n'):
                    item = item.strip()
                    if item and item.startswith('- '):
                        item = item[2:].strip()
                    if item:
                        updates["conversation_details"].append(item)

        return updates, important_updates
    except Exception as e:
        print(f"Error extracting memory: {e}")
        return {
            "world_facts": [],
            "character_development": [],
            "relationships": [],
            "plot_developments": [],
            "player_decisions": [],
            "environment_details": [],
            "conversation_details": []
        }, []


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


def update_game_state(game_state, player_input, dm_response, model):
    """Update game state based on player input and DM response, with dynamic element creation"""
    # Add to conversation history
    current_session = game_state['game_info']['session_count']

    # Find current session or create new one
    session_found = False
    for session in game_state['conversation_history']:
        if session['session'] == current_session:
            session['exchanges'].append({"speaker": "Player", "text": player_input})
            session['exchanges'].append({"speaker": "DM", "text": dm_response})
            session_found = True
            break

    if not session_found:
        game_state['conversation_history'].append({
            "session": current_session,
            "exchanges": [
                {"speaker": "Player", "text": player_input},
                {"speaker": "DM", "text": dm_response}
            ]
        })

    # Get plot pacing preference
    plot_pace = game_state['game_info'].get('plot_pace', 'Balanced')

    # Extract and update narrative memory - now returns important updates separately
    memory_updates, important_updates = extract_memory_updates(
        player_input,
        dm_response,
        game_state['narrative_memory'],
        model,
        plot_pace
    )

    # Add new memory items without duplicates
    for category, items in memory_updates.items():
        if category not in game_state['narrative_memory']:
            game_state['narrative_memory'][category] = []

        for item in items:
            if item not in game_state['narrative_memory'][category]:
                game_state['narrative_memory'][category].append(item)

    # Dynamic element creation - Add new NPCs
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

    # Dynamic element creation - Add new locations
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

    # Store important updates for potential notification
    if important_updates:
        game_state['important_updates'] = important_updates

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


def create_new_story():
    """Create a new story by gathering player input"""
    colored_print("\n=== CREATE NEW STORY ===\n", Colors.SYSTEM)

    player_input = {}

    # Get available models and let player choose
    available_models = get_available_ollama_models()
    colored_print("\n--- SELECT AI MODEL ---", Colors.SYSTEM)
    colored_print("Available models:", Colors.SYSTEM)

    for i, model_name in enumerate(available_models, 1):
        colored_print(f"{i}. {model_name}", Colors.SYSTEM)

    while True:
        model_choice = input("\nChoose a model (number or name): ")

        if model_choice.isdigit() and 1 <= int(model_choice) <= len(available_models):
            selected_model = available_models[int(model_choice) - 1]
            player_input["model_name"] = selected_model
            break
        elif model_choice in available_models:
            player_input["model_name"] = model_choice
            break
        else:
            colored_print("Invalid choice. Please select a valid model.", Colors.SYSTEM)

    # Get basic story info
    player_input["story_title"] = input("Story title: ")
    player_input["world_name"] = input("World name: ")
    player_input["genre"] = input("Genre (fantasy, sci-fi, western, etc.): ")
    player_input["setting"] = input("Setting description: ")
    player_input["tone"] = input("Tone (dark, lighthearted, mysterious, etc.): ")

    # Get content rating
    colored_print("\n--- CONTENT RATING ---", Colors.SYSTEM)
    colored_print("E: Family-friendly - No graphic violence, no sexual content", Colors.SYSTEM)
    colored_print("T: Teen - Some violence, dark themes, mild suggestive themes", Colors.SYSTEM)
    colored_print("M: Mature - Graphic violence, sexual themes, intense content", Colors.SYSTEM)

    while True:
        rating = input("Choose a rating (E/T/M): ").upper()
        if rating in ["E", "T", "M"]:
            player_input["rating"] = rating
            break
        else:
            colored_print("Invalid rating. Please choose E, T, or M.", Colors.SYSTEM)

    # Get plot pacing preference
    colored_print("\n--- PLOT PACING ---", Colors.SYSTEM)
    colored_print("Fast-paced: Quick plot advancement with frequent developments and challenges", Colors.SYSTEM)
    colored_print("Balanced: Mix of character moments with regular plot advancement", Colors.SYSTEM)
    colored_print("Slice-of-life: Emphasize character interactions with slow, organic plot development", Colors.SYSTEM)

    while True:
        pace = input("Choose plot pacing (Fast-paced/Balanced/Slice-of-life): ").capitalize()
        if pace in ["Fast-paced", "Balanced", "Slice-of-life"]:
            player_input["plot_pace"] = pace
            break
        elif pace.lower() == "fast":
            player_input["plot_pace"] = "Fast-paced"
            break
        elif pace.lower() == "slice" or pace.lower() == "life":
            player_input["plot_pace"] = "Slice-of-life"
            break
        else:
            colored_print("Invalid choice. Please choose Fast-paced, Balanced, or Slice-of-life.", Colors.SYSTEM)

    # Get player character info
    colored_print("\n--- CHARACTER CREATION ---", Colors.SYSTEM)
    player_input["character_name"] = input("Your character's name: ")
    player_input["character_race"] = input("Your character's race: ")
    player_input["character_class"] = input("Your character's class/profession: ")

    traits = input("Character traits (comma separated): ")
    if traits:
        player_input["character_traits"] = [t.strip() for t in traits.split(",")]

    abilities = input("Character abilities (comma separated): ")
    if abilities:
        player_input["abilities"] = [a.strip() for a in abilities.split(",")]

    # Get starting location
    colored_print("\n--- STARTING LOCATION ---", Colors.SYSTEM)
    player_input["starting_location_name"] = input("Starting location name: ")
    player_input["starting_location_description"] = input("Starting location description: ")

    # Get initial quest
    colored_print("\n--- INITIAL QUEST ---", Colors.SYSTEM)
    player_input["quest_name"] = input("Initial quest name: ")
    player_input["quest_description"] = input("Initial quest description: ")

    # Get world facts
    colored_print("\n--- WORLD FACTS ---", Colors.SYSTEM)
    facts = input("Enter some facts about your world (comma separated): ")
    if facts:
        player_input["world_facts"] = [f.strip() for f in facts.split(",")]

    # Get NPCs (optional)
    colored_print("\n--- NPCS (Optional) ---", Colors.SYSTEM)
    colored_print("Would you like to add NPCs? (Type 'done' when finished)", Colors.SYSTEM)

    npcs = []
    while True:
        npc_name = input("\nNPC name (or 'done' to finish): ")
        if npc_name.lower() == 'done':
            break

        npc = {"name": npc_name}
        npc["race"] = input("NPC race: ")
        npc["description"] = input("NPC description: ")
        npc["disposition"] = input("NPC disposition (friendly, hostile, neutral): ")
        npc["motivation"] = input("NPC motivation: ")
        npc["dialogue_style"] = input("NPC dialogue style: ")

        npcs.append(npc)

    if npcs:
        player_input["npcs"] = npcs

    return player_input


def manage_stories():
    """Allow users to delete stories"""
    stories = list_stories()

    if not stories:
        colored_print("No stories found to manage.", Colors.SYSTEM)
        return

    colored_print("\n=== MANAGE STORIES ===", Colors.SYSTEM)
    colored_print("Select a story to delete:", Colors.SYSTEM)

    for i, (file_name, story_title) in enumerate(stories, 1):
        colored_print(f"{i}. {story_title} [{file_name}]", Colors.SYSTEM)

    colored_print(f"{len(stories) + 1}. Return to main menu", Colors.SYSTEM)

    while True:
        choice = input("\nEnter story number to delete (or 'cancel'): ")
        if choice.lower() == 'cancel':
            return

        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(stories):
                file_name, story_title = stories[choice_num - 1]

                # Confirm deletion
                confirm = input(f"Are you sure you want to delete '{story_title}'? (yes/no): ")
                if confirm.lower() == 'yes':
                    if delete_story(file_name):
                        colored_print(f"Story '{story_title}' deleted successfully.", Colors.SYSTEM)
                        return
                else:
                    colored_print("Deletion cancelled.", Colors.SYSTEM)
            elif choice_num == len(stories) + 1:
                return

        colored_print("Invalid choice. Please try again.", Colors.SYSTEM)


def handle_game():
    """Main game loop with story selection"""
    colored_print("\n=== DUNGEON MASTER AI ===\n", Colors.SYSTEM)
    colored_print("1. Create a new story", Colors.SYSTEM)
    colored_print("2. Load an existing story", Colors.SYSTEM)
    colored_print("3. Manage stories", Colors.SYSTEM)
    colored_print("4. Exit", Colors.SYSTEM)

    choice = input("\nChoose an option (1-4): ")

    if choice == "4":
        colored_print("Goodbye!", Colors.SYSTEM)
        return

    if choice == "3":
        manage_stories()
        # Return to main menu after managing stories
        handle_game()
        return

    story_name = None
    game_state = None

    if choice == "1":
        # Create new story
        player_input = create_new_story()
        game_state = init_game_state(player_input)
        story_name = player_input["story_title"]

        # Initialize the model with player's choice
        model = OllamaLLM(model=game_state["game_info"]["model_name"])

        # Create a custom prompt for this story
        prompt = ChatPromptTemplate.from_template(dm_template)
        chain = prompt | model

        # Generate initial narration
        colored_print("\nCreating your world...", Colors.SYSTEM)
        context = generate_context(game_state)
        initial_prompt = "Please provide a brief introduction to this world and the beginning of my adventure."

        intro_response = chain.invoke({
            'genre': game_state['game_info']['genre'],
            'world_name': game_state['game_info']['world_name'],
            'setting_description': game_state['game_info']['setting'],
            'tone': game_state['game_info']['tone'],
            'rating': game_state['game_info']['rating'],
            'plot_pace': game_state['game_info']['plot_pace'],
            'context': context,
            'question': initial_prompt
        })

        # Add the intro to conversation history
        game_state['conversation_history'][0]['exchanges'].append(
            {"speaker": "Player", "text": initial_prompt}
        )
        game_state['conversation_history'][0]['exchanges'].append(
            {"speaker": "DM", "text": intro_response}
        )

        # Add initial narrative memory (silently)
        initial_memory, important_updates = extract_memory_updates(
            initial_prompt,
            intro_response,
            game_state['narrative_memory'],
            model,
            game_state['game_info']['plot_pace']
        )

        # Update memory
        for category, items in initial_memory.items():
            if category not in game_state['narrative_memory']:
                game_state['narrative_memory'][category] = []
            game_state['narrative_memory'][category].extend(items)

        # Save the initial game state
        save_game_state(game_state, story_name)

        sys.stdout.write(f"{Colors.DM_NAME}DM: {Colors.RESET}")
        colored_print(intro_response, Colors.DM_TEXT)


    elif choice == "2":
        # Load existing story
        stories = list_stories()
        if not stories:
            colored_print("No existing stories found.", Colors.SYSTEM)
            return

        colored_print("\n=== AVAILABLE STORIES ===", Colors.SYSTEM)

        for i, (file_name, story_title) in enumerate(stories, 1):
            colored_print(f"{i}. {story_title} [{file_name}]", Colors.SYSTEM)
        story_choice = input("\nChoose a story number or type its name: ")

        # Handle selection by number or name
        if story_choice.isdigit() and 1 <= int(story_choice) <= len(stories):
            file_name, story_name = stories[int(story_choice) - 1]
        else:

            # Try to find by name
            matched = False
            for file_name, title in stories:
                if story_choice.lower() in file_name.lower() or story_choice.lower() in title.lower():
                    story_name = title
                    matched = True
                    break

            if not matched:
                colored_print("Story not found.", Colors.SYSTEM)
                return

        # Load the selected story
        game_state = load_game_state(file_name)

        if not game_state:
            colored_print("Error loading story. The save file might be corrupted.", Colors.SYSTEM)
            return

        # Only proceed if game_state is successfully loaded
        model_name = game_state["game_info"].get("model_name", "mistral-small")

        # Initialize the model with the saved choice
        model = OllamaLLM(model=model_name)

        # Check if model name exists in game state, and if not (for backwards compatibility), ask user to choose
        if "model_name" not in game_state["game_info"]:
            # Let user choose model for this existing story
            available_models = get_available_ollama_models()
            colored_print("\nThis story doesn't have an AI model set. Please choose one now:", Colors.SYSTEM)
            colored_print("Available models:", Colors.SYSTEM)

            for i, model_name in enumerate(available_models, 1):
                colored_print(f"{i}. {model_name}", Colors.SYSTEM)

            while True:
                model_choice = input("\nChoose a model (number or name): ")

                if model_choice.isdigit() and 1 <= int(model_choice) <= len(available_models):
                    selected_model = available_models[int(model_choice) - 1]
                    game_state["game_info"]["model_name"] = selected_model
                    model = OllamaLLM(model=selected_model)
                    break
                elif model_choice in available_models:
                    game_state["game_info"]["model_name"] = model_choice
                    model = OllamaLLM(model=model_choice)
                    break
                else:
                    colored_print("Invalid choice. Please select a valid model.", Colors.SYSTEM)

        # Handle selection by number or name
        if story_choice.isdigit() and 1 <= int(story_choice) <= len(stories):
            file_name, story_name = stories[int(story_choice) - 1]
        else:
            # Try to find by name
            matched = False
            for file_name, title in stories:
                if story_choice.lower() in file_name.lower() or story_choice.lower() in title.lower():
                    story_name = title
                    matched = True
                    break

            if not matched:
                colored_print("Story not found.", Colors.SYSTEM)
                return

        # Load the selected story
        game_state = load_game_state(file_name)
        if not game_state:
            colored_print("Error loading story.", Colors.SYSTEM)
            return

        story_name = game_state['game_info']['title']
        colored_print(f"\nLoaded story: {story_name}", Colors.SYSTEM)

        # Check if rating exists, add if not (for backwards compatibility)
        if 'rating' not in game_state['game_info']:
            colored_print("This story doesn't have a content rating set. Please choose one now:", Colors.SYSTEM)
            colored_print("E: Family-friendly - No graphic violence, no sexual content", Colors.SYSTEM)
            colored_print("T: Teen - Some violence, dark themes, mild suggestive themes", Colors.SYSTEM)
            colored_print("M: Mature - Graphic violence, sexual themes, intense content", Colors.SYSTEM)

            while True:
                rating = input("Choose a rating (E/T/M): ").upper()
                if rating in ["E", "T", "M"]:
                    game_state['game_info']['rating'] = rating
                    break
                else:
                    colored_print("Invalid rating. Please choose E, T, or M.", Colors.SYSTEM)

        # Check if plot pacing exists, add if not (for backwards compatibility)
        if 'plot_pace' not in game_state['game_info']:
            colored_print("This story doesn't have plot pacing set. Please choose one now:", Colors.SYSTEM)
            colored_print("Fast-paced: Quick plot advancement with frequent developments and challenges", Colors.SYSTEM)
            colored_print("Balanced: Mix of character moments with regular plot advancement", Colors.SYSTEM)
            colored_print("Slice-of-life: Emphasize character interactions with slow, organic plot development",
                          Colors.SYSTEM)

            while True:
                pace = input("Choose plot pacing (Fast-paced/Balanced/Slice-of-life): ").capitalize()
                if pace in ["Fast-paced", "Balanced", "Slice-of-life"]:
                    game_state['game_info']['plot_pace'] = pace
                    break
                elif pace.lower() == "fast":
                    game_state['game_info']['plot_pace'] = "Fast-paced"
                    break
                elif pace.lower() == "slice" or pace.lower() == "life":
                    game_state['game_info']['plot_pace'] = "Slice-of-life"
                    break
                else:
                    colored_print("Invalid choice. Please choose Fast-paced, Balanced, or Slice-of-life.",
                                  Colors.SYSTEM)

        # Check if narrative memory exists, add if not (for backwards compatibility)
        if 'narrative_memory' not in game_state:
            game_state['narrative_memory'] = {
                "world_facts": [],
                "character_development": [],
                "relationships": [],
                "plot_developments": [],
                "player_decisions": [],
                "environment_details": [],
                "conversation_details": []
            }

            # Rebuild narrative memory from conversation history
            colored_print("Rebuilding narrative memory from history...", Colors.SYSTEM)
            all_exchanges = []
            for session in game_state['conversation_history']:
                all_exchanges.extend(session['exchanges'])

            # Process exchanges in pairs
            for i in range(0, len(all_exchanges), 2):
                if i + 1 < len(all_exchanges):
                    player_input = all_exchanges[i]['text']
                    dm_response = all_exchanges[i + 1]['text']

                    # Extract memory updates
                    memory_updates, _ = extract_memory_updates(
                        player_input,
                        dm_response,
                        game_state['narrative_memory'],
                        model,
                        game_state['game_info'].get('plot_pace', 'Balanced')
                    )

                    # Add memory items
                    for category, items in memory_updates.items():
                        if category not in game_state['narrative_memory']:
                            game_state['narrative_memory'][category] = []
                        for item in items:
                            if item not in game_state['narrative_memory'][category]:
                                game_state['narrative_memory'][category].append(item)

        # Add environment_details and conversation_details if missing
        if 'environment_details' not in game_state['narrative_memory']:
            game_state['narrative_memory']['environment_details'] = []
        if 'conversation_details' not in game_state['narrative_memory']:
            game_state['narrative_memory']['conversation_details'] = []

        # Create a custom prompt for this story
        prompt = ChatPromptTemplate.from_template(dm_template)
        chain = prompt | model

        # Show last exchange
        if (game_state['conversation_history'] and
                game_state['conversation_history'][-1]['exchanges']):
            last_exchange = game_state['conversation_history'][-1]['exchanges'][-1]
            sys.stdout.write(f"{Colors.DM_NAME}{last_exchange['speaker']}: {Colors.RESET}")
            colored_print(last_exchange['text'], Colors.DM_TEXT)
    else:
        colored_print("Invalid choice.", Colors.SYSTEM)
        return

    # Main game loop
    colored_print("\nType 'exit' or 'quit' to leave the game.", Colors.SYSTEM)
    colored_print("Type 'save' to save your progress.", Colors.SYSTEM)
    colored_print("Type 'memory' to see the current narrative memory.", Colors.SYSTEM)
    colored_print("Type 'summary' to see a recap of the story so far.", Colors.SYSTEM)

    while True:
        sys.stdout.write(f"{Colors.PLAYER}You: {Colors.RESET}")
        player_input = input()

        if player_input.lower() in ['exit', 'quit']:
            save_game_state(game_state, story_name)
            colored_print("Game saved. Goodbye!", Colors.SYSTEM)
            break

        if player_input.lower() == 'save':
            save_game_state(game_state, story_name)
            colored_print("Game saved!", Colors.SYSTEM)
            continue

        if player_input.lower() == 'summary':
            # Generate narrative summary
            colored_print("\n=== THE STORY SO FAR ===", Colors.SYSTEM)

            # Get the narrative summary
            narrative_summary = generate_story_summary(game_state, model)

            # Process the summary to highlight important parts (those in bold)
            # We'll split it into paragraphs for better readability
            paragraphs = narrative_summary.split("\n\n")

            for paragraph in paragraphs:
                # Split by bold markers if any were preserved
                if "**" in paragraph:
                    parts = paragraph.split("**")
                    for i, part in enumerate(parts):
                        # Every odd-indexed part was meant to be bold
                        if i % 2 == 1:
                            colored_print(part, Colors.DM_NAME)  # Highlight important parts
                        else:
                            colored_print(part, Colors.DM_TEXT)
                else:
                    # No bold formatting, just print normally
                    colored_print(paragraph, Colors.DM_TEXT)

                # Add spacing between paragraphs
                print()

            continue

        if player_input.lower() == 'memory':
            colored_print("\n=== NARRATIVE MEMORY ===", Colors.SYSTEM)
            memory = game_state['narrative_memory']

            colored_print("World facts:", Colors.SYSTEM)
            for item in memory['world_facts']:
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nCharacter development:", Colors.SYSTEM)
            for item in memory['character_development']:
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nRelationships:", Colors.SYSTEM)
            for item in memory['relationships']:
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nPlot developments:", Colors.SYSTEM)
            for item in memory['plot_developments']:
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nImportant player decisions:", Colors.SYSTEM)
            for item in memory['player_decisions']:
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nEnvironment details:", Colors.SYSTEM)
            for item in memory.get('environment_details', []):
                colored_print(f"- {item}", Colors.SYSTEM)

            colored_print("\nConversation details:", Colors.SYSTEM)
            for item in memory.get('conversation_details', []):
                colored_print(f"- {item}", Colors.SYSTEM)

            continue

        # Clear previous important updates
        game_state['important_updates'] = []

        # Generate context from game state
        context = generate_context(game_state)

        # Get DM response
        dm_response = chain.invoke({
            'genre': game_state['game_info']['genre'],
            'world_name': game_state['game_info']['world_name'],
            'setting_description': game_state['game_info']['setting'],
            'tone': game_state['game_info']['tone'],
            'rating': game_state['game_info']['rating'],
            'plot_pace': game_state['game_info']['plot_pace'],
            'context': context,
            'question': player_input
        })

        sys.stdout.write(f"{Colors.DM_NAME}DM: {Colors.RESET}")
        colored_print(dm_response, Colors.DM_TEXT)

        # Update game state with silent memory tracking
        game_state = update_game_state(game_state, player_input, dm_response, model)

        # Show important updates only if they exist
        if game_state['important_updates']:
            colored_print("\n! Important developments:", Colors.SYSTEM)
            for update in game_state['important_updates']:
                colored_print(f"* {update}", Colors.SYSTEM)

        # Save after each turn
        save_game_state(game_state, story_name)


if __name__ == '__main__':
    handle_game()