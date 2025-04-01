import subprocess
import os
import glob
import re
import json
import requests

# Directory for storing game stories
STORIES_DIR = "rpg_stories"
os.makedirs(STORIES_DIR, exist_ok=True)

# Enhanced DM prompt template with expanded dynamic world creation guidelines and game state commands
dm_template = """
You are an experienced Dungeon Master for a {genre} RPG set in {world_name}. Your role is to:

1. Create an immersive world with rich descriptions that engage all senses
2. Portray NPCs with consistent personalities, goals, and knowledge
3. Present appropriate challenges and opportunities for character development
4. Maintain narrative continuity and remember details from previous sessions
5. Apply game rules fairly while prioritizing storytelling and player enjoyment
6. Adapt the story based on player choices to create a truly interactive experience

CRITICAL OUTPUT REQUIREMENTS:
- RESPONSE LENGTH: {response_length_instruction}
- VARIETY: Never use similar sentence structures back-to-back
- PRECISION: Use specific, evocative details rather than general descriptions, but avoid being too verbose
- UNIQUENESS: Avoid reusing phrases, descriptions, or scene transitions
- FREEDOM: Only give the player specific choices when absolutely necessary, otherwise always simply ask "What will you do?" to end your output
- GAMEPLAY: The player character should never speak on their own, unless the user tells them to in their responses. You will never generate dialogue from their perspective
- ROLE CONSISTENCY: Always respond in role as the Dungeon Master or as an NPC character when speaking. Never break character to respond as an AI model. Never mention AI models, prompts, or language processing. Stay completely immersed in the fantasy role.
- FORBIDDEN PHRASES: Never use phrases like "I can't create content that is...", "As an AI, I...", "I'm sorry, but I cannot...", or any similar statements that break immersion.
- NARRATIVE VOICE: When describing scenes, use the voice of a storyteller. When NPCs speak, use their established personalities and dialogue patterns.
- FINISHING OUTPUT: Always end your output, no matter what it is, with "What will you do?"

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

GAME STATE COMMANDS:
When significant changes happen in the game, include one or more of the following commands hidden in your response, enclosed in double square brackets. These commands help the game system track the story correctly:

- To complete a quest: [[QUEST_COMPLETE:Quest Name]]
- To introduce a new NPC: [[NEW_CHARACTER:Character Name|Race|Description|Disposition|Motivation|Dialogue Style]]
- To discover a new location: [[NEW_LOCATION:Location Name|Description|Ambience]]
- To add a new item: [[NEW_ITEM:Item Name|Description|Properties]]
- To start a new quest: [[NEW_QUEST:Quest Name|Description|Giver]]
- To record an important memory: [[MEMORY:Category|Description]]

For example:
- If the player retrieves a stolen amulet: [[QUEST_COMPLETE:Recover the Stolen Amulet]]
- If they meet a new character: [[NEW_CHARACTER:Captain Morgan|Human|A grizzled sailor with a scar across his face|friendly|Seeking passage to the northern isles|Speaks with a thick accent and sailor's vocabulary]]

Include these commands ONLY when appropriate state changes occur. Hide these commands naturally within your narrative text - they will be automatically removed before being shown to the player.

AVAILABLE QUESTS:
{active_quests}

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


class GameStateManager:
    """Centralized manager for direct game state updates"""

    def __init__(self, game_state):
        self.game_state = game_state

    def process_update_commands(self, response_text):
        """Process all game state update commands in the text and return cleaned text"""
        # Extract all commands
        commands = re.findall(r'\[\[(.*?)\]\]', response_text)

        # Process each command
        important_updates = []
        for command in commands:
            if command.startswith('QUEST_COMPLETE:'):
                quest_name = command[14:].strip()
                if self.complete_quest(quest_name):
                    important_updates.append(f"Quest completed: {quest_name}")

            elif command.startswith('NEW_CHARACTER:'):
                char_data = command[14:].strip().split('|')
                if len(char_data) >= 1:
                    char_name = char_data[0].strip()
                    char_race = char_data[1].strip() if len(char_data) > 1 else "Human"
                    char_desc = char_data[2].strip() if len(char_data) > 2 else f"A character named {char_name}"
                    char_disp = char_data[3].strip() if len(char_data) > 3 else "neutral"
                    char_motiv = char_data[4].strip() if len(char_data) > 4 else "unknown"
                    char_style = char_data[5].strip() if len(char_data) > 5 else "speaks normally"

                    if self.add_character(char_name, char_race, char_desc, char_disp, char_motiv, char_style):
                        important_updates.append(f"New character: {char_name}")

            elif command.startswith('NEW_LOCATION:'):
                loc_data = command[13:].strip().split('|')
                if len(loc_data) >= 1:
                    loc_name = loc_data[0].strip()
                    loc_desc = loc_data[1].strip() if len(loc_data) > 1 else f"A place called {loc_name}"
                    loc_amb = loc_data[2].strip() if len(loc_data) > 2 else "The atmosphere is distinct and memorable."

                    if self.add_location(loc_name, loc_desc, loc_amb):
                        important_updates.append(f"New location: {loc_name}")

            elif command.startswith('NEW_ITEM:'):
                item_data = command[9:].strip().split('|')
                if len(item_data) >= 1:
                    item_name = item_data[0].strip()
                    item_desc = item_data[1].strip() if len(item_data) > 1 else f"An item called {item_name}"
                    item_props = item_data[2].strip() if len(item_data) > 2 else "No special properties."

                    if self.add_item(item_name, item_desc, item_props):
                        important_updates.append(f"New item: {item_name}")

            elif command.startswith('NEW_QUEST:'):
                quest_data = command[10:].strip().split('|')
                if len(quest_data) >= 1:
                    quest_name = quest_data[0].strip()
                    quest_desc = quest_data[1].strip() if len(quest_data) > 1 else f"A quest to {quest_name}"
                    quest_giver = quest_data[2].strip() if len(quest_data) > 2 else "narrator"

                    if self.add_quest(quest_name, quest_desc, quest_giver):
                        important_updates.append(f"New quest: {quest_name}")

            elif command.startswith('MEMORY:'):
                mem_data = command[7:].strip().split('|')
                if len(mem_data) >= 2:
                    category = mem_data[0].strip().lower().replace(' ', '_')
                    description = mem_data[1].strip()

                    if self.add_memory(category, description):
                        if category == "plot_developments":
                            important_updates.append(f"Plot: {description}")

        # Store important updates
        if important_updates:
            if 'important_updates' not in self.game_state:
                self.game_state['important_updates'] = []
            self.game_state['important_updates'].extend(important_updates)

        # Remove all commands from the text
        cleaned_text = re.sub(r'\[\[.*?\]\]', '', response_text)
        return cleaned_text

    def complete_quest(self, quest_name):
        """Complete a quest by name"""
        for quest_id, quest in self.game_state['quests'].items():
            if quest['name'].lower() == quest_name.lower():
                if quest['status'] != "completed":
                    quest['status'] = "completed"

                    # Mark all steps as completed
                    for step in quest['steps']:
                        step['completed'] = True

                    print(f"Quest completed: {quest_name}")
                    return True
        return False

    def add_character(self, name, race="Human", description="", disposition="neutral",
                      motivation="unknown", dialogue_style="speaks normally"):
        """Add a new character if they don't already exist"""
        # Skip if name is empty or too short
        if not name or len(name) < 2:
            return False

        # Check if this character already exists
        for npc_id, npc in self.game_state['npcs'].items():
            if npc['name'].lower() == name.lower():
                # Character already exists
                return False

        # Create a safe ID
        npc_id = "npc_" + "".join([c.lower() if c.isalnum() else "_" for c in name])

        # Create the character
        self.game_state['npcs'][npc_id] = {
            "name": name,
            "race": race,
            "description": description,
            "location": self.game_state['game_info']['current_location'],
            "disposition": disposition,
            "motivation": motivation,
            "knowledge": [],
            "relationships": {},
            "dialogue_style": dialogue_style
        }

        # Add to current location
        current_loc = self.game_state['game_info']['current_location']
        if npc_id not in self.game_state['locations'][current_loc]['npcs_present']:
            self.game_state['locations'][current_loc]['npcs_present'].append(npc_id)

        # Add to narrative memory
        if 'new_npcs' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['new_npcs'] = []

        memory_entry = f"Met {name}, a {race.lower()} {disposition} character."
        if memory_entry not in self.game_state['narrative_memory']['new_npcs']:
            self.game_state['narrative_memory']['new_npcs'].append(memory_entry)

        print(f"New character added: {name}")
        return True

    def add_location(self, name, description="", ambience=""):
        """Add a new location if it doesn't already exist"""
        # Skip if name is empty or too short
        if not name or len(name) < 2:
            return False

        # Check if this location already exists
        for loc_id, loc in self.game_state['locations'].items():
            if loc['name'].lower() == name.lower():
                # Location already exists
                return False

        # Create a safe ID
        loc_id = "location_" + "".join([c.lower() if c.isalnum() else "_" for c in name])

        # Get current location for connection
        current_loc = self.game_state['game_info']['current_location']

        # Create the location
        self.game_state['locations'][loc_id] = {
            "name": name,
            "description": description,
            "ambience": ambience,
            "connected_to": [current_loc],
            "npcs_present": [],
            "points_of_interest": [],
            "secrets": [],
            "available_quests": [],
            "visited": False
        }

        # Add connection from current location
        if loc_id not in self.game_state['locations'][current_loc]['connected_to']:
            self.game_state['locations'][current_loc]['connected_to'].append(loc_id)

        # Add to narrative memory
        if 'new_locations' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['new_locations'] = []

        memory_entry = f"Discovered {name}, a new location."
        if memory_entry not in self.game_state['narrative_memory']['new_locations']:
            self.game_state['narrative_memory']['new_locations'].append(memory_entry)

        print(f"New location added: {name}")
        return True

    def add_item(self, name, description="", properties=""):
        """Add a new item if it doesn't already exist"""
        # Skip if name is empty or too short
        if not name or len(name) < 2:
            return False

        # Initialize items dict if it doesn't exist
        if 'items' not in self.game_state:
            self.game_state['items'] = {}

        # Check if this item already exists
        for item_id, item in self.game_state['items'].items():
            if item['name'].lower() == name.lower():
                # Item already exists
                return False

        # Create a safe ID
        item_id = "item_" + "".join([c.lower() if c.isalnum() else "_" for c in name])

        # Create the item
        self.game_state['items'][item_id] = {
            "name": name,
            "description": description,
            "properties": properties,
            "location": self.game_state['game_info']['current_location'],
            "owner": None
        }

        # Add to narrative memory
        if 'new_items' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['new_items'] = []

        memory_entry = f"Found {name}, a new item."
        if memory_entry not in self.game_state['narrative_memory']['new_items']:
            self.game_state['narrative_memory']['new_items'].append(memory_entry)

        # Add to player inventory
        pc_id = list(self.game_state['player_characters'].keys())[0]
        if name not in self.game_state['player_characters'][pc_id]['inventory']:
            self.game_state['player_characters'][pc_id]['inventory'].append(name)

        print(f"New item added: {name}")
        return True

    def add_quest(self, name, description="", giver="narrator"):
        """Add a new quest if it doesn't already exist"""
        # Skip if name is empty or too short
        if not name or len(name) < 2:
            return False

        # Check if this quest already exists
        for quest_id, quest in self.game_state['quests'].items():
            if quest['name'].lower() == name.lower():
                # Quest already exists
                return False

        # Create a safe ID
        quest_id = "quest_" + "".join([c.lower() if c.isalnum() else "_" for c in name])

        # Create the quest
        self.game_state['quests'][quest_id] = {
            "name": name,
            "description": description,
            "status": "active",
            "giver": giver,
            "steps": [
                {"id": "begin_quest", "description": f"Begin {name}", "completed": False}
            ],
            "difficulty": "standard",
            "time_sensitive": False
        }

        # Add to player's quest list
        pc_id = list(self.game_state['player_characters'].keys())[0]
        if quest_id not in self.game_state['player_characters'][pc_id]['quests']:
            self.game_state['player_characters'][pc_id]['quests'].append(quest_id)

        # Add to current location's available quests
        current_loc = self.game_state['game_info']['current_location']
        if quest_id not in self.game_state['locations'][current_loc]['available_quests']:
            self.game_state['locations'][current_loc]['available_quests'].append(quest_id)

        # Add to narrative memory
        if 'new_quests' not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory']['new_quests'] = []

        memory_entry = f"Started new quest: {name}."
        if memory_entry not in self.game_state['narrative_memory']['new_quests']:
            self.game_state['narrative_memory']['new_quests'].append(memory_entry)

        print(f"New quest added: {name}")
        return True

    def add_memory(self, category, description):
        """Add a new memory entry to a category"""
        # Skip if description is empty
        if not description:
            return False

        # Check category exists
        valid_categories = [
            "world_facts", "character_development", "relationships",
            "plot_developments", "player_decisions", "environment_details",
            "conversation_details"
        ]

        if category not in valid_categories:
            category = "world_facts"  # Default category

        # Initialize category if it doesn't exist
        if category not in self.game_state['narrative_memory']:
            self.game_state['narrative_memory'][category] = []

        # Add memory if not already present
        if description not in self.game_state['narrative_memory'][category]:
            self.game_state['narrative_memory'][category].append(description)
            print(f"Added memory to {category}: {description}")
            return True

        return False


class OllamaLLM:
    """Direct implementation for Ollama models without LangChain dependencies"""

    def __init__(self, model="mistral-small", temperature=0.7, top_p=0.9, top_k=40, max_tokens=None):
        self.model_name = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.api_base = "http://localhost:11434/api"

    def invoke(self, prompt):
        """Invoke the model with the given prompt"""
        # Handle different input types to extract the text content
        if isinstance(prompt, dict):
            if "question" in prompt:
                input_text = prompt["question"]
            elif "content" in prompt:
                input_text = prompt["content"]
            else:
                # Try to extract from other common keys
                for key in ["text", "prompt", "input"]:
                    if key in prompt:
                        input_text = prompt[key]
                        break
                else:
                    # If no known keys found, serialize the whole dict
                    input_text = json.dumps(prompt)
        elif isinstance(prompt, str):
            input_text = prompt
        else:
            # Try to convert other types to string
            input_text = str(prompt)

        # Build the request payload
        payload = {
            "model": self.model_name,
            "prompt": input_text,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
            }
        }

        if self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens

        # Make the API request
        try:
            response = requests.post(f"{self.api_base}/generate", json=payload)
            response.raise_for_status()

            # Parse the response
            result = response.json()
            if "response" in result:
                return result["response"]
            else:
                return f"Error: Unexpected response format: {result}"

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            # Try to salvage what we can from the response
            try:
                text = response.text
                # For streaming responses with multiple JSON objects
                if '\n' in text:
                    # Take just the first complete JSON object
                    first_json = text.split('\n')[0]
                    obj = json.loads(first_json)
                    if "response" in obj:
                        return obj["response"]
                return f"Error parsing JSON response: {e}. Raw response: {text[:100]}..."
            except Exception as inner_e:
                return f"Error processing response: {inner_e}"
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            return f"Error: {str(e)}"

    def stream(self, prompt):
        """Stream the model's response as individual tokens with robust error handling"""
        # Similar input handling as invoke
        if isinstance(prompt, dict):
            if "question" in prompt:
                input_text = prompt["question"]
            elif "content" in prompt:
                input_text = prompt["content"]
            else:
                for key in ["text", "prompt", "input"]:
                    if key in prompt:
                        input_text = prompt[key]
                        break
                else:
                    input_text = json.dumps(prompt)
        elif isinstance(prompt, str):
            input_text = prompt
        else:
            input_text = str(prompt)

        payload = {
            "model": self.model_name,
            "prompt": input_text,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
            }
        }

        if self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens

        try:
            # Make a streaming request
            response = requests.post(
                f"{self.api_base}/generate",
                json=payload,
                stream=True
            )

            response.raise_for_status()

            # Process the streaming response
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    # Try to parse the JSON line
                    data = json.loads(line.decode('utf-8'))
                    if "response" in data:
                        yield data["response"]
                except json.JSONDecodeError as e:
                    print(f"JSON error in stream: {e}")
                    # Try to extract content even if JSON is malformed
                    line_str = line.decode('utf-8')
                    if '"response": "' in line_str:
                        # Extract text between response quotes
                        try:
                            start = line_str.index('"response": "') + 13
                            end = line_str.rindex('"')
                            if start < end:
                                yield line_str[start:end]
                        except:
                            # If extraction fails, just yield what we have
                            yield f"[Error parsing stream response]"

        except Exception as e:
            print(f"Error streaming from Ollama API: {e}")
            yield f"Error generating response: {str(e)}"

    def update_settings(self, temperature=None, top_p=None, top_k=None, max_tokens=None):
        """Update the model settings"""
        if temperature is not None:
            self.temperature = temperature
        if top_p is not None:
            self.top_p = top_p
        if top_k is not None:
            self.top_k = top_k
        if max_tokens is not None:
            self.max_tokens = max_tokens

    def change_model(self, model_name):
        """Change the model"""
        self.model_name = model_name


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
            "days_passed": 0,
            "temperature": 0.7,  # Default temperature
            "top_p": 0.9,  # Default top_p
            "max_tokens": 2048  # Default max tokens
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

    # Add active quests list
    active_quests = []
    for quest_id in pc['quests']:
        if quest_id in game_state['quests'] and game_state['quests'][quest_id]['status'] == 'active':
            active_quests.append(game_state['quests'][quest_id]['name'])

    if active_quests:
        context += "\nActive quests:\n"
        for quest_name in active_quests:
            context += f"- {quest_name}\n"

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
    """Extract memory updates without using LangChain pipelines"""
    # Create a string representation of current memory
    memory_str = ""
    for category, items in current_memory.items():
        if items:
            memory_str += f"{category.replace('_', ' ').title()}:\n"
            for item in items:
                memory_str += f"- {item}\n"

    # Format the full prompt directly
    full_prompt = f"""
Based on the following exchange, extract important narrative information to remember:

Player: {player_input}
DM: {dm_response}

Current narrative memory:
{memory_str}

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

    # Get memory updates
    try:
        # Directly invoke the model with our prompt
        memory_response = model.invoke(full_prompt)
        print(f"Memory response received, length: {len(memory_response)}")

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
            # Fixed regex patterns for extracting categories
            # World facts
            world_facts_pattern = r"(?:World facts?|1[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[2-9]|Character development|Relationships|Plot|Player|Environment|Conversation|New NPCs|New locations|New items|New quests|$))"
            world_facts = re.findall(world_facts_pattern, memory_response, re.DOTALL)

            # Character development
            character_dev_pattern = r"(?:Character development|2[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[3-9]|Relationships|Plot|Player|Environment|Conversation|New NPCs|New locations|New items|New quests|$))"
            character_dev = re.findall(character_dev_pattern, memory_response, re.DOTALL)

            # Relationships
            relationships_pattern = r"(?:Relationships?|3[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[4-9]|Plot|Player|Environment|Conversation|New NPCs|New locations|New items|New quests|$))"
            relationships = re.findall(relationships_pattern, memory_response, re.DOTALL)

            # Plot developments
            plot_dev_pattern = r"(?:Plot developments?|4[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[5-9]|Player|Important decisions|Environment|Conversation|New NPCs|New locations|New items|New quests|$))"
            plot_dev = re.findall(plot_dev_pattern, memory_response, re.DOTALL)

            # Player decisions
            decisions_pattern = r"(?:Player decisions|Important decisions|5[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[6-9]|Environment|Conversation|New NPCs|New locations|New items|New quests|$))"
            decisions = re.findall(decisions_pattern, memory_response, re.DOTALL)

            # Environment details
            environment_pattern = r"(?:Environment details|6[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[7-9]|Conversation|New NPCs|New locations|New items|New quests|$))"
            environment = re.findall(environment_pattern, memory_response, re.DOTALL)

            # Conversation details
            conversation_pattern = r"(?:Conversation details|7[\.\)]):?\s*(.+?)(?=(?:\n\n|\n[8-9]|New NPCs|New locations|New items|New quests|$))"
            conversation = re.findall(conversation_pattern, memory_response, re.DOTALL)

            # New NPCs
            new_npcs_pattern = r"(?:New NPCs|8[\.\)]):?\s*(.+?)(?=(?:\n\n|\n9|New locations|New items|New quests|$))"
            new_npcs = re.findall(new_npcs_pattern, memory_response, re.DOTALL)

            # New locations
            new_locations_pattern = r"(?:New locations|9[\.\)]):?\s*(.+?)(?=(?:\n\n|\n10|New items|New quests|$))"
            new_locations = re.findall(new_locations_pattern, memory_response, re.DOTALL)

            # New items
            new_items_pattern = r"(?:New items|10[\.\)]):?\s*(.+?)(?=(?:\n\n|\n11|New quests|$))"
            new_items = re.findall(new_items_pattern, memory_response, re.DOTALL)

            # New quests
            new_quests_pattern = r"(?:New quests|11[\.\)]):?\s*(.+?)(?=(?:\n\n|$))"
            new_quests = re.findall(new_quests_pattern, memory_response, re.DOTALL)

            # Process categories with improved item extraction
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
                    # Clean up and process each item in the category
                    for content in category_matches:
                        # Split by newlines and process each item
                        lines = content.strip().split('\n')
                        for line in lines:
                            # Clean up formatting
                            line = line.strip()
                            # Remove bullet points, asterisks, and other formatting
                            if line.startswith('- '):
                                line = line[2:].strip()
                            if line.startswith('* '):
                                line = line[2:].strip()
                            if line.startswith('• '):
                                line = line[2:].strip()

                            # Remove unwanted formatting artifacts
                            line = re.sub(r"or actions taken:?\s*\*+\s*", "", line)
                            line = re.sub(r"\*+\s*", "", line)

                            # Only add non-empty, meaningful lines
                            if line and len(line) > 3:
                                updates[category_name].append(line)

                                # Add to important updates based on category and pacing
                                if category_name == "plot_developments":
                                    if plot_pace == "Fast-paced":
                                        important_updates.append(f"Plot: {line}")
                                    elif plot_pace == "Balanced" and any(
                                            keyword in line.lower() for keyword in ["significant", "major", "reveal"]):
                                        important_updates.append(f"Plot: {line}")
                                    elif plot_pace == "Slice-of-life" and any(
                                            keyword in line.lower() for keyword in ["major revelation", "crucial"]):
                                        important_updates.append(f"Plot: {line}")
                                elif category_name == "new_npcs":
                                    important_updates.append(f"New Character: {line}")
                                elif category_name == "new_locations":
                                    important_updates.append(f"New Location: {line}")
                                elif category_name == "new_quests":
                                    important_updates.append(f"New Quest: {line}")
                                elif category_name == "new_items" and any(
                                        keyword in line.lower() for keyword in ["significant", "powerful", "unique"]):
                                    important_updates.append(f"New Item: {line}")

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


def update_game_state(game_state, player_input, dm_response, model):
    """Update the game state based on player input and DM response with direct update system"""
    # Create game state manager
    manager = GameStateManager(game_state)

    # Process any direct update commands in the DM's response
    cleaned_response = manager.process_update_commands(dm_response)

    # Add to conversation history (with cleaned response)
    current_session = game_state['game_info']['session_count']

    # Find current session or create new one
    session_found = False
    for session in game_state['conversation_history']:
        if session['session'] == current_session:
            session['exchanges'].append({"speaker": "Player", "text": player_input})
            session['exchanges'].append({"speaker": "DM", "text": cleaned_response})
            session_found = True
            break

    if not session_found:
        game_state['conversation_history'].append({
            "session": current_session,
            "exchanges": [
                {"speaker": "Player", "text": player_input},
                {"speaker": "DM", "text": cleaned_response}
            ]
        })

    # Get plot pacing preference
    plot_pace = game_state['game_info'].get('plot_pace', 'Balanced')

    # Update memory
    memory_updates, important_updates = extract_memory_updates(
        player_input,
        cleaned_response,  # Use the cleaned response without commands
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

    # Include the important updates from memory extraction
    if important_updates:
        if 'important_updates' not in game_state:
            game_state['important_updates'] = []
        game_state['important_updates'].extend(important_updates)

    # Save the game state
    story_name = game_state['game_info']['title']
    save_game_state(game_state, story_name)

    return game_state


def generate_story_summary(game_state, model):
    """Generate a narrative summary of the story so far without using LangChain pipelines"""
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

    # Create direct prompt for summary generation
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

    # Generate the summary directly
    try:
        narrative_summary = model.invoke(summary_prompt)
        return narrative_summary
    except Exception as e:
        print(f"Error generating summary: {e}")
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
    """Generate a DM response with dynamic quest handling"""
    # Get model settings from game state
    temperature = game_state['game_info'].get('temperature', 0.7)
    top_p = game_state['game_info'].get('top_p', 0.9)
    max_tokens = game_state['game_info'].get('max_tokens', 2048)
    response_length = game_state['game_info'].get('response_length', 3)  # Default: Medium

    # Define response length instructions
    response_length_instructions = {
        1: "EXTREMELY BRIEF: Keep responses very short, 1-2 sentences maximum. Be direct and to the point.",
        2: "BRIEF: Keep responses concise, 2-3 sentences maximum. Include only essential details.",
        3: "MEDIUM: Use a balanced length for responses, 4-6 sentences. Include moderate description.",
        4: "DETAILED: Provide detailed responses with rich descriptions, 7-10 sentences. Elaborate on surroundings and emotions.",
        5: "VERY DETAILED: Be highly detailed and descriptive in responses, 11+ sentences. Use vivid, immersive descriptions and elaborate on all sensory details."
    }

    response_length_instruction = response_length_instructions.get(response_length, response_length_instructions[3])

    # Dynamically gather active quests for the prompt
    active_quests = []

    # First, get the current main quest if it exists
    current_quest_id = game_state['game_info'].get('current_quest')
    if current_quest_id and current_quest_id in game_state['quests']:
        current_quest = game_state['quests'][current_quest_id]
        if current_quest['status'] == 'active':
            active_quests.append(f"- {current_quest['name']} (MAIN): {current_quest['description']}")

    # Then add other active quests
    pc_id = list(game_state['player_characters'].keys())[0]
    for quest_id in game_state['player_characters'][pc_id]['quests']:
        if quest_id in game_state['quests'] and game_state['quests'][quest_id][
            'status'] == 'active' and quest_id != current_quest_id:
            quest = game_state['quests'][quest_id]
            active_quests.append(f"- {quest['name']}: {quest['description']}")

    active_quests_text = "\n".join(active_quests) if active_quests else "None"

    # Create model instance
    model = OllamaLLM(model=model_name, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

    # Generate context from game state
    context = generate_context(game_state)

    # Create the prompt using dm_template with dynamic active quests
    prompt = dm_template.format(
        genre=game_state['game_info']['genre'],
        world_name=game_state['game_info']['world_name'],
        setting_description=game_state['game_info']['setting'],
        tone=game_state['game_info']['tone'],
        rating=game_state['game_info'].get('rating', 'T'),
        plot_pace=game_state['game_info'].get('plot_pace', 'Balanced'),
        response_length_instruction=response_length_instruction,
        active_quests=active_quests_text,
        context=context,
        question=player_input
    )

    # Get DM response
    dm_response = model.invoke(prompt)

    # Process commands and update game state
    # Create a GameStateManager instance
    manager = GameStateManager(game_state)

    # Process the commands in the response and get the cleaned response
    cleaned_response = manager.process_update_commands(dm_response)

    # Update game state with the cleaned response
    updated_game_state = update_game_state(game_state, player_input, cleaned_response, model)

    # Extract important updates
    important_updates = updated_game_state.get('important_updates', [])

    return cleaned_response, updated_game_state, important_updates


def initialize_new_story(model_name, story_data):
    """Initialize a new story with the provided data without using LangChain pipelines"""
    game_state = init_game_state(story_data)

    # Get model settings
    temperature = game_state['game_info'].get('temperature', 0.7)
    top_p = game_state['game_info'].get('top_p', 0.9)
    max_tokens = game_state['game_info'].get('max_tokens', 2048)

    model = OllamaLLM(model=model_name, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

    # Generate initial narration directly
    context = generate_context(game_state)
    initial_prompt = "Please provide a brief introduction to this world and the beginning of my adventure."

    # Active quests for the prompt
    active_quests = []
    for quest_id, quest in game_state['quests'].items():
        if quest['status'] == 'active':
            active_quests.append(f"- {quest['name']}: {quest['description']}")

    active_quests_text = "\n".join(active_quests) if active_quests else "None"

    # Create the prompt directly
    full_prompt = dm_template.format(
        genre=game_state['game_info']['genre'],
        world_name=game_state['game_info']['world_name'],
        setting_description=game_state['game_info']['setting'],
        tone=game_state['game_info']['tone'],
        rating=game_state['game_info'].get('rating', 'T'),
        plot_pace=game_state['game_info'].get('plot_pace', 'Balanced'),
        response_length_instruction="MEDIUM: Use a balanced length for responses, 4-6 sentences. Include moderate description.",
        active_quests=active_quests_text,
        context=context,
        question=initial_prompt
    )

    intro_response = model.invoke(full_prompt)

    # Process commands in the intro response
    manager = GameStateManager(game_state)
    cleaned_intro = manager.process_update_commands(intro_response)

    # Add the intro to conversation history
    game_state['conversation_history'][0]['exchanges'].append(
        {"speaker": "Player", "text": initial_prompt}
    )
    game_state['conversation_history'][0]['exchanges'].append(
        {"speaker": "DM", "text": cleaned_intro}
    )

    # Add initial narrative memory
    initial_memory, important_updates = extract_memory_updates(
        initial_prompt,
        cleaned_intro,
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

    return game_state, cleaned_intro