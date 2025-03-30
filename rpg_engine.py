﻿from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import subprocess
import json
import os
import glob
import re

# Directory for storing game stories
STORIES_DIR = "rpg_stories"
os.makedirs(STORIES_DIR, exist_ok=True)

# Enhanced DM prompt template with expanded dynamic world creation guidelines
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
You are expected to actively create new elements to build a rich, evolving world:
- Create new NPCs with distinct personalities, motivations, relationships, and quirks
- Develop new locations as the story progresses, each with unique atmosphere and purpose
- Introduce new items, objects, and artifacts that have significance to the world or story
- Create new quests, challenges, and opportunities as they emerge naturally from the narrative
- Add cultural elements, local customs, festivals, or historical events relevant to the setting
- All new elements should be consistent with the established world and appropriate for the plot pacing

When creating new elements:
- Introduce them organically through the narrative, never forcing them into the story
- Provide vivid, specific descriptions that make them memorable and distinct
- Establish clear connections to existing elements and the overall world
- Give names to important new elements so they can be referenced consistently
- Use sensory details to make locations feel real and immersive
- Give NPCs distinct speech patterns, mannerisms, or physical characteristics
- Remember all details you create and reference them consistently in future interactions

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
"""

# Enhanced memory update prompt with more categories and detailed extraction guidance
memory_update_template = """
Based on the following exchange, extract important narrative information to remember:

Player: {player_input}
DM: {dm_response}

Current narrative memory:
{current_memory}

Plot pacing style: {plot_pace}

Extract NEW information about:
1. World facts (new locations, history, customs, cultural elements, environment)
2. Character development (player or NPCs, personality traits, abilities, motivations)
3. Relationships (how characters relate to each other, alliances, rivalries, attractions)
4. Plot development (story progression, revelations, mysteries, goals)
5. Important decisions or actions taken (player choices, consequences, achievements)
6. Environment details (room descriptions, objects, atmosphere, sensory details)
7. Conversation details (important dialogue, information shared, questions raised)
8. New NPCs (names, descriptions, roles, distinctive traits)
9. New locations (names, descriptions, atmosphere, significance)
10. New items (names, descriptions, properties, significance)
11. New quests or missions (goals, requirements, rewards, related characters)

For "Fast-paced" stories, highlight all plot developments.
For "Balanced" stories, highlight only significant plot developments.
For "Slice-of-life" stories, highlight only major plot revelations or developments.

Format each piece as a brief, factual statement.
Return ONLY new information not already in the narrative memory.
Keep each entry concise (max 15 words).
If no new information was revealed, return "No new information to record."

New information to add to memory:
"""


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
            "conversation_details": [],
            "new_npcs": [],
            "new_locations": [],
            "new_items": [],
            "new_quests": []
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
    return file_path


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

    # Environment details
    if 'environment_details' in game_state['narrative_memory'] and game_state['narrative_memory'][
        'environment_details']:
        context += "Environment details:\n"
        for detail in game_state['narrative_memory']['environment_details']:
            context += f"- {detail}\n"

    # Conversation details
    if 'conversation_details' in game_state['narrative_memory'] and game_state['narrative_memory'][
        'conversation_details']:
        context += "Conversation details:\n"
        for detail in game_state['narrative_memory']['conversation_details']:
            context += f"- {detail}\n"

    # New NPCs
    if 'new_npcs' in game_state['narrative_memory'] and game_state['narrative_memory']['new_npcs']:
        context += "Recently encountered NPCs:\n"
        for npc in game_state['narrative_memory']['new_npcs']:
            context += f"- {npc}\n"

    # New locations
    if 'new_locations' in game_state['narrative_memory'] and game_state['narrative_memory']['new_locations']:
        context += "Recently discovered locations:\n"
        for location in game_state['narrative_memory']['new_locations']:
            context += f"- {location}\n"

    # New items
    if 'new_items' in game_state['narrative_memory'] and game_state['narrative_memory']['new_items']:
        context += "Recently acquired or encountered items:\n"
        for item in game_state['narrative_memory']['new_items']:
            context += f"- {item}\n"

    # New quests
    if 'new_quests' in game_state['narrative_memory'] and game_state['narrative_memory']['new_quests']:
        context += "Recently started quests or missions:\n"
        for quest in game_state['narrative_memory']['new_quests']:
            context += f"- {quest}\n"

    # Add relevant world facts
    context += "\nWorld knowledge:\n"
    for fact in game_state['world_facts']:
        context += f"- {fact}\n"

    # Add recent conversation history
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
            "conversation_details": [],
            "new_npcs": [],
            "new_locations": [],
            "new_items": [],
            "new_quests": []
        }

        # Track important updates for player notification
        important_updates = []

        if "No new information to record" not in memory_response:
            # Extract categories with regex
            world_facts = re.findall(
                r"World facts?:?\s*(.+?)(?=Character|\n\n|Environment|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response, re.DOTALL)
            character_dev = re.findall(
                r"Character development:?\s*(.+?)(?=Relationship|\n\n|Environment|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response,
                re.DOTALL)
            relationships = re.findall(
                r"Relationships?:?\s*(.+?)(?=Plot|\n\n|Environment|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response, re.DOTALL)
            plot_dev = re.findall(
                r"Plot developments?:?\s*(.+?)(?=Player|\n\n|Environment|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response, re.DOTALL)
            decisions = re.findall(
                r"(?:Player decisions|Important decisions):?\s*(.+?)(?=\n\n|Environment|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response, re.DOTALL)
            environment = re.findall(
                r"Environment details:?\s*(.+?)(?=\n\n|Conversation|New NPCs|New locations|New items|New quests|$)",
                memory_response,
                re.DOTALL)
            conversation = re.findall(
                r"Conversation details:?\s*(.+?)(?=\n\n|New NPCs|New locations|New items|New quests|$)",
                memory_response, re.DOTALL)
            new_npcs = re.findall(r"New NPCs:?\s*(.+?)(?=\n\n|New locations|New items|New quests|$)", memory_response,
                                  re.DOTALL)
            new_locations = re.findall(r"New locations:?\s*(.+?)(?=\n\n|New NPCs|New items|New quests|$)",
                                       memory_response, re.DOTALL)
            new_items = re.findall(r"New items:?\s*(.+?)(?=\n\n|New NPCs|New locations|New quests|$)", memory_response,
                                   re.DOTALL)
            new_quests = re.findall(r"New quests:?\s*(.+?)(?=\n\n|New NPCs|New locations|New items|$)", memory_response,
                                    re.DOTALL)

            # Process categories
            categories = [
                (world_facts, "world_facts"),
                (character_dev, "character_development"),
                (relationships, "relationships"),
                (plot_dev, "plot_developments"),
                (decisions, "player_decisions"),
                (environment, "environment_details"),
                (conversation, "conversation_details"),
                (new_npcs, "new_npcs"),
                (new_locations, "new_locations"),
                (new_items, "new_items"),
                (new_quests, "new_quests")
            ]

            for category_matches, category_name in categories:
                if category_matches:
                    for item in category_matches[0].strip().split('\n'):
                        item = item.strip()
                        if item and item.startswith('- '):
                            item = item[2:].strip()
                        if item:
                            updates[category_name].append(item)

                            # Add to important updates based on category and pacing
                            if category_name == "plot_developments":
                                if plot_pace == "Fast-paced":
                                    important_updates.append(f"Plot: {item}")
                                elif plot_pace == "Balanced" and any(
                                        keyword in item.lower() for keyword in ["significant", "major", "reveal"]):
                                    important_updates.append(f"Plot: {item}")
                                elif plot_pace == "Slice-of-life" and any(
                                        keyword in item.lower() for keyword in ["major revelation", "crucial"]):
                                    important_updates.append(f"Plot: {item}")
                            elif category_name == "new_npcs":
                                important_updates.append(f"New Character: {item}")
                            elif category_name == "new_locations":
                                important_updates.append(f"New Location: {item}")
                            elif category_name == "new_quests":
                                important_updates.append(f"New Quest: {item}")
                            elif category_name == "new_items" and any(
                                    keyword in item.lower() for keyword in ["significant", "powerful", "unique"]):
                                important_updates.append(f"New Item: {item}")

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
            "conversation_details": [],
            "new_npcs": [],
            "new_locations": [],
            "new_items": [],
            "new_quests": []
        }, []


def update_dynamic_elements(game_state, memory_updates):
    """Updates game state with new elements the AI has created using enhanced detection patterns"""

    # Extract potential new NPCs from memory updates and direct scanning of text
    for category in ['character_development', 'relationships', 'plot_developments', 'new_npcs']:
        for item in memory_updates.get(category, []):
            # Enhanced patterns that look for more natural introductions of characters
            npc_patterns = [
                r"(?:new character|new npc|newcomer|stranger|visitor|figure)(?:\s+named|\s+called)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                r"(?:met|encountered|approached by|introduced to|greeted by|spoken to by)(?:\s+a)?\s+(?:[a-z]+\s+)?(?:named|called)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s+(?:a|an|the)\s+[a-z]+)?\s+(?:enters|appears|arrives|joins|approached|introduces|revealed)",
                r"(?:a|an)\s+(?:new|mysterious|strange|unexpected|local)\s+(?:person|individual|character|figure|man|woman)\s+(?:named|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
            ]

            npc_name = None
            for pattern in npc_patterns:
                npc_match = re.search(pattern, item, re.IGNORECASE)
                if npc_match:
                    npc_name = npc_match.group(1).strip()
                    break

            if npc_name:
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
                    race_match = re.search(
                        r"(?:a|an)\s+([a-z]+)\s+(?:man|woman|person|being|elf|dwarf|orc|goblin|creature)", item,
                        re.IGNORECASE)
                    if race_match:
                        race = race_match.group(1).capitalize()

                    # Extract description
                    description = "A character recently introduced to the story."
                    desc_match = re.search(r"(?:described as|appears to be|looks like|seems to be)\s+([^\.]+)", item,
                                           re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group(1).strip()

                    # Extract disposition
                    disposition = "neutral"
                    disp_match = re.search(r"(?:disposition|attitude|demeanor)\s+(?:is|seems|appears)\s+([^\.]+)", item,
                                           re.IGNORECASE)
                    if disp_match:
                        disp_text = disp_match.group(1).lower().strip()
                        if "friendly" in disp_text or "kind" in disp_text or "warm" in disp_text:
                            disposition = "friendly"
                        elif "hostile" in disp_text or "aggressive" in disp_text or "angry" in disp_text:
                            disposition = "hostile"

                    # Extract dialogue style
                    dialogue_style = "speaks normally"
                    style_match = re.search(r"(?:speaks|talks|voice is|tone is|manner of speech is)\s+([^\.]+)", item,
                                            re.IGNORECASE)
                    if style_match:
                        dialogue_style = style_match.group(1).strip()

                    # Extract motivation
                    motivation = "unknown"
                    motiv_match = re.search(r"(?:wants|seeks|desires|motivated by|goal is|aims to)\s+([^\.]+)", item,
                                            re.IGNORECASE)
                    if motiv_match:
                        motivation = motiv_match.group(1).strip()

                    # Create basic NPC entry with enhanced details
                    game_state['npcs'][npc_id] = {
                        "name": npc_name,
                        "race": race,
                        "description": description,
                        "location": game_state['game_info']['current_location'],
                        "disposition": disposition,
                        "motivation": motivation,
                        "knowledge": [],
                        "relationships": {},
                        "dialogue_style": dialogue_style
                    }

                    # Add NPC to current location
                    current_loc = game_state['game_info']['current_location']
                    if npc_id not in game_state['locations'][current_loc]['npcs_present']:
                        game_state['locations'][current_loc]['npcs_present'].append(npc_id)

    # Extract potential new locations with enhanced patterns
    for category in ['world_facts', 'plot_developments', 'environment_details', 'new_locations']:
        for item in memory_updates.get(category, []):
            # Enhanced patterns that look for more natural introductions of locations
            location_patterns = [
                r"(?:new location|new place|new area|new building|new room|new site)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:discover|found|entered|reached|arrived at|came to)(?:ed|s)?\s+(?:a|an|the)?\s+(?:place|location|area|building|room|site)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:a|an|the)\s+(?:place|location|area|building|room|site)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"([A-Z][a-z\s']+)(?:\s+is\s+a\s+)(?:new|nearby|local|mysterious|strange|hidden|secret|ancient|forgotten)\s+(?:place|location|area|building|room|site)"
            ]

            location_name = None
            for pattern in location_patterns:
                location_match = re.search(pattern, item, re.IGNORECASE)
                if location_match:
                    location_name = location_match.group(1).strip()
                    break

            if location_name:
                # Check if this location already exists
                location_exists = False
                for loc_id in game_state['locations']:
                    if game_state['locations'][loc_id]['name'].lower() == location_name.lower():
                        location_exists = True
                        break

                # Create new location if it doesn't exist
                if not location_exists:
                    loc_id = "location_" + "".join([c.lower() if c.isalnum() else "_" for c in location_name])

                    # Extract description
                    description = "A place recently discovered in the story."
                    desc_match = re.search(r"(?:described as|appears to be|looks like|seems to be)\s+([^\.]+)", item,
                                           re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group(1).strip()

                    # Extract ambience
                    ambience = "The atmosphere is yet to be fully experienced."
                    amb_match = re.search(r"(?:atmosphere|ambience|feel|aura|mood)\s+(?:is|seems|appears)\s+([^\.]+)",
                                          item, re.IGNORECASE)
                    if amb_match:
                        ambience = amb_match.group(1).strip()

                    # Get current location to create connection
                    current_loc = game_state['game_info']['current_location']

                    # Create enhanced location entry
                    game_state['locations'][loc_id] = {
                        "name": location_name,
                        "description": description,
                        "ambience": ambience,
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

    # Extract potential new items with enhanced patterns
    for category in ['environment_details', 'plot_developments', 'new_items']:
        for item in memory_updates.get(category, []):
            # Enhanced patterns that look for more natural introductions of items
            item_patterns = [
                r"(?:new item|new object|new artifact|new weapon|new tool)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:found|discovered|obtained|acquired|given|received)(?:s|ed)?\s+(?:a|an|the)?\s+(?:item|object|artifact|weapon|tool)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:a|an|the)\s+(?:mysterious|ancient|powerful|magical|special|unique|strange)\s+(?:item|object|artifact|weapon|tool)(?:\s+called|\s+named)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"([A-Z][a-z\s']+)(?:\s+is\s+a\s+)(?:new|mysterious|ancient|powerful|magical|special|unique|strange)\s+(?:item|object|artifact|weapon|tool)"
            ]

            item_name = None
            for pattern in item_patterns:
                item_match = re.search(pattern, item, re.IGNORECASE)
                if item_match:
                    item_name = item_match.group(1).strip()
                    break

            if item_name:
                # Check if this item already exists
                item_exists = False
                for it_id in game_state.get('items', {}):
                    if game_state['items'][it_id]['name'].lower() == item_name.lower():
                        item_exists = True
                        break

                # Create new item if it doesn't exist
                if not item_exists:
                    item_id = "item_" + "".join([c.lower() if c.isalnum() else "_" for c in item_name])

                    # Extract description
                    description = "An object recently discovered in the story."
                    desc_match = re.search(r"(?:described as|appears to be|looks like|seems to be)\s+([^\.]+)", item,
                                           re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group(1).strip()

                    # Extract properties
                    properties = "Has no special properties."
                    prop_match = re.search(
                        r"(?:properties|abilities|powers|functions|capabilities)\s+(?:include|are|being)\s+([^\.]+)",
                        item, re.IGNORECASE)
                    if prop_match:
                        properties = prop_match.group(1).strip()

                    # Create item entry with enhanced details
                    if 'items' not in game_state:
                        game_state['items'] = {}

                    game_state['items'][item_id] = {
                        "name": item_name,
                        "description": description,
                        "properties": properties,
                        "location": game_state['game_info']['current_location'],
                        "owner": None
                    }

                    # Consider adding to player inventory if appropriate
                    if "found" in item.lower() or "acquired" in item.lower() or "obtained" in item.lower() or "received" in item.lower() or "given" in item.lower():
                        pc_id = list(game_state['player_characters'].keys())[0]
                        if item_id not in game_state['player_characters'][pc_id]['inventory']:
                            game_state['player_characters'][pc_id]['inventory'].append(item_name)

    # Extract potential new quests with enhanced patterns
    for category in ['plot_developments', 'conversation_details', 'new_quests']:
        for item in memory_updates.get(category, []):
            # Enhanced patterns that look for more natural introductions of quests
            quest_patterns = [
                r"(?:new quest|new mission|new task|new objective|new challenge)(?:\s+called|\s+named|to)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:assigned|given|tasked with|accepted|undertook|started)(?:s|ed)?\s+(?:a|an|the)?\s+(?:quest|mission|task|objective|challenge)(?:\s+called|\s+named|to)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"(?:a|an|the)\s+(?:important|dangerous|urgent|mysterious|secret|difficult)\s+(?:quest|mission|task|objective|challenge)(?:\s+called|\s+named|to)?\s+(?:the|a|an)?\s*([A-Z][a-z\s']+)",
                r"([A-Z][a-z\s']+)(?:\s+is\s+a\s+)(?:new|important|dangerous|urgent|mysterious|secret|difficult)\s+(?:quest|mission|task|objective|challenge)"
            ]

            quest_name = None
            for pattern in quest_patterns:
                quest_match = re.search(pattern, item, re.IGNORECASE)
                if quest_match:
                    quest_name = quest_match.group(1).strip()
                    break

            if quest_name:
                # Check if this quest already exists
                quest_exists = False
                for q_id in game_state['quests']:
                    if game_state['quests'][q_id]['name'].lower() == quest_name.lower():
                        quest_exists = True
                        break

                # Create new quest if it doesn't exist
                if not quest_exists:
                    quest_id = "quest_" + "".join([c.lower() if c.isalnum() else "_" for c in quest_name])

                    # Extract description
                    description = "A mission recently uncovered in the story."
                    desc_match = re.search(r"(?:involves|requires|entails|about|concerning)\s+([^\.]+)", item,
                                           re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group(1).strip()

                    # Extract giver
                    giver = "unknown"
                    giver_match = re.search(r"(?:given by|assigned by|from|offered by)\s+([^\.]+)", item, re.IGNORECASE)
                    if giver_match:
                        giver = giver_match.group(1).strip()

                    # Create quest entry with enhanced details
                    game_state['quests'][quest_id] = {
                        "name": quest_name,
                        "description": description,
                        "status": "active",
                        "giver": giver,
                        "steps": [
                            {"id": "begin_quest", "description": f"Begin {quest_name}", "completed": False}
                        ],
                        "difficulty": "standard",
                        "time_sensitive": False
                    }

                    # Consider updating player quests
                    pc_id = list(game_state['player_characters'].keys())[0]
                    if quest_id not in game_state['player_characters'][pc_id]['quests']:
                        game_state['player_characters'][pc_id]['quests'].append(quest_id)

                    # Add to available quests at current location
                    current_loc = game_state['game_info']['current_location']
                    if quest_id not in game_state['locations'][current_loc]['available_quests']:
                        game_state['locations'][current_loc]['available_quests'].append(quest_id)

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

    # Apply enhanced dynamic element creation
    game_state = update_dynamic_elements(game_state, memory_updates)

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
    new_npcs = game_state['narrative_memory'].get('new_npcs', [])
    new_locations = game_state['narrative_memory'].get('new_locations', [])
    new_items = game_state['narrative_memory'].get('new_items', [])
    new_quests = game_state['narrative_memory'].get('new_quests', [])

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

    New Characters:
    {' '.join(new_npcs)}

    New Locations:
    {' '.join(new_locations)}

    New Items:
    {' '.join(new_items)}

    New Quests:
    {' '.join(new_quests)}

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


def generate_dm_response(game_state, player_input, model_name):
    """Generate a DM response for the player input"""
    model = OllamaLLM(model=model_name)
    prompt = ChatPromptTemplate.from_template(dm_template)
    chain = prompt | model

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

    # Update game state
    updated_game_state = update_game_state(game_state, player_input, dm_response, model)

    # Extract important updates
    important_updates = updated_game_state.get('important_updates', [])

    return dm_response, updated_game_state, important_updates


def initialize_new_story(model_name, story_data):
    """Initialize a new story with the provided data"""
    game_state = init_game_state(story_data)
    model = OllamaLLM(model=model_name)

    # Create a custom prompt for this story
    prompt = ChatPromptTemplate.from_template(dm_template)
    chain = prompt | model

    # Generate initial narration
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

    # Add initial narrative memory
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

    # Save the game state
    save_game_state(game_state, game_state['game_info']['title'])

    return game_state, intro_response