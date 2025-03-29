"""

User interface for the AI RPG memory system.

"""



import os

import sys

import cmd

import json

import time

import logging

from typing import Dict, List, Any, Optional, Tuple



from memory_system import MemorySystem

from llm_interface import LLMInterface

from config import DEFAULT_CAMPAIGN_NAME



# Set up logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)





class GameInterface(cmd.Cmd):

    """

    Command-line interface for the AI RPG memory system.

    """



    intro = """

    ========================================================

      AI RPG Memory System - Advanced Campaign Management

    ========================================================

    Type 'help' to see available commands.

    Type 'new' to create a new campaign.

    Type 'load' to load an existing campaign.

    Type 'exit' to quit.

    """



    prompt = "> "



    def __init__(self):

        """Initialize the game interface."""

        super().__init__()

        self.llm = LLMInterface()

        self.memory_system = None

        self.campaign_loaded = False



    # Command: new

    def do_new(self, arg):

        """Create a new campaign."""

        print("\nCreating a new campaign...")



        # Ask for campaign name

        campaign_name = input("Campaign name: ")

        if not campaign_name:

            campaign_name = DEFAULT_CAMPAIGN_NAME



        # Initialize memory system

        self.memory_system = MemorySystem(campaign_name=campaign_name, llm_interface=self.llm)



        # Initial setup options

        print("\nInitial Setup Options:")

        print("1. Empty campaign")

        print("2. Basic setup (starter location and character)")

        print("3. Import from JSON file")



        choice = input("Choose an option (1-3): ")



        if choice == "2":

            # Basic setup

            initial_setup = self._create_basic_setup()

            self.memory_system.create_campaign(campaign_name, initial_setup)

        elif choice == "3":

            # Import from JSON

            file_path = input("Enter path to JSON file: ")

            if os.path.exists(file_path):

                try:

                    with open(file_path, "r") as f:

                        initial_setup = json.load(f)

                    self.memory_system.create_campaign(campaign_name, initial_setup)

                except Exception as e:

                    print(f"Error importing from JSON: {e}")

                    self.memory_system.create_campaign(campaign_name, {})

            else:

                print("File not found. Creating empty campaign.")

                self.memory_system.create_campaign(campaign_name, {})

        else:

            # Empty campaign

            self.memory_system.create_campaign(campaign_name, {})



        self.campaign_loaded = True

        print(f"\nCampaign '{campaign_name}' created successfully.")

        print("Type 'play' to start playing or 'help' to see available commands.")



    # Command: load

    def do_load(self, arg):

        """Load an existing campaign."""

        print("\nAvailable campaigns:")



        # Create temporary memory system to get available campaigns

        temp_system = MemorySystem(llm_interface=self.llm)

        campaigns = temp_system.get_available_campaigns()



        if not campaigns:

            print("No campaigns found.")

            return



        # Display available campaigns

        for i, campaign in enumerate(campaigns):

            print(f"{i + 1}. {campaign['name']} (ID: {campaign['id']})")



        # Ask for campaign to load

        choice = input("\nEnter number of campaign to load (or 'c' to cancel): ")



        if choice.lower() == 'c':

            return



        try:

            index = int(choice) - 1

            if 0 <= index < len(campaigns):

                campaign_id = campaigns[index]["id"]



                # Initialize memory system and load campaign

                self.memory_system = MemorySystem(llm_interface=self.llm)

                success = self.memory_system.load_campaign(campaign_id)



                if success:

                    self.campaign_loaded = True

                    print(f"\nCampaign '{self.memory_system.campaign_name}' loaded successfully.")

                    print("Type 'play' to start playing or 'help' to see available commands.")

                else:

                    print("Failed to load campaign.")

            else:

                print("Invalid selection.")

        except ValueError:

            print("Invalid input.")



    # Command: play

    def do_play(self, arg):

        """Start or continue playing the campaign."""

        if not self.campaign_loaded:

            print("No campaign loaded. Use 'new' or 'load' first.")

            return



        print(f"\n=== {self.memory_system.campaign_name} ===")

        print("(Type '/help' during play for in-game commands, or just '/exit' to return to the main menu)\n")



        # Get current location

        current_location = None

        if self.memory_system.current_focus.get("location"):

            location_id = self.memory_system.current_focus["location"]

            location = self.memory_system.card_manager.get_card(location_id)

            if location:

                current_location = location.name



        # Print current status

        if current_location:

            print(f"Current location: {current_location}")



        # Characters present

        character_ids = self.memory_system.current_focus.get("characters", [])

        if character_ids:

            character_names = []

            for char_id in character_ids:

                character = self.memory_system.card_manager.get_card(char_id)

                if character:

                    character_names.append(character.name)



            if character_names:

                print(f"Characters present: {', '.join(character_names)}")



        print("\nGame started. What would you like to do?\n")



        # Start game loop

        while True:

            user_input = input("YOU: ")



            # Check for in-game commands

            if user_input.startswith('/'):

                command = user_input[1:].strip().lower()



                if command == 'exit':

                    break

                elif command == 'help':

                    self._show_in_game_help()

                elif command == 'status':

                    self._show_game_status()

                elif command == 'chars' or command == 'characters':

                    self._show_characters()

                elif command == 'loc' or command == 'location':

                    self._show_location()

                elif command == 'items':

                    self._show_items()

                elif command == 'stories':

                    self._show_stories()

                elif command.startswith('char '):

                    self._show_character_details(command[5:])

                elif command.startswith('item '):

                    self._show_item_details(command[5:])

                elif command.startswith('loc '):

                    self._show_location_details(command[4:])

                elif command.startswith('story '):

                    self._show_story_details(command[6:])

                else:

                    print("Unknown command. Type '/help' for available commands.")

            else:

                # Process game input

                response = self.memory_system.process_turn(user_input)

                print(f"\nGM: {response}\n")



    # Command: status

    def do_status(self, arg):

        """Show the status of the current campaign."""

        if not self.campaign_loaded:

            print("No campaign loaded. Use 'new' or 'load' first.")

            return



        summary = self.memory_system.get_campaign_summary()



        print(f"\n=== Campaign: {summary['name']} ===")

        print(f"ID: {summary['id']}")

        print("\nStats:")

        print(f"- Characters: {summary['stats']['characters']}")

        print(f"- Locations: {summary['stats']['locations']}")

        print(f"- Items: {summary['stats']['items']}")

        print(f"- Stories: {summary['stats']['stories']}")

        print(f"- Relationships: {summary['stats']['relationships']}")

        print(f"- Interactions: {summary['stats']['interactions']}")



        if summary['current_location']:

            print(f"\nCurrent Location: {summary['current_location']['name']}")



        if summary['active_characters']:

            print("\nActive Characters:")

            for char in summary['active_characters']:

                print(f"- {char['name']}")



        if summary['active_stories']:

            print("\nActive Stories:")

            for story in summary['active_stories']:

                print(f"- {story['name']}")



    # Command: check

    def do_check(self, arg):

        """Run a consistency check on the game state."""

        if not self.campaign_loaded:

            print("No campaign loaded. Use 'new' or 'load' first.")

            return



        print("\nRunning consistency check...")

        results = self.memory_system.run_consistency_check()



        print(f"\nFound {results['counts']['total']} potential inconsistencies:")

        print(f"- High severity: {results['counts']['by_severity']['high']}")

        print(f"- Medium severity: {results['counts']['by_severity']['medium']}")

        print(f"- Low severity: {results['counts']['by_severity']['low']}")



        if results['counts']['total'] > 0:

            print("\nInconsistencies by type:")

            for type_key, count in results['counts']['by_type'].items():

                print(f"- {type_key}: {count}")



            show_details = input("\nShow detailed inconsistencies? (y/n): ")

            if show_details.lower() == 'y':

                print("\nDetailed inconsistencies:")

                for inconsistency in results['inconsistencies']:

                    entity_id = inconsistency.get("entity_id", "Unknown")

                    entity_name = inconsistency.get("entity_name", entity_id)

                    description = inconsistency.get("description", "No description")

                    severity = inconsistency.get("severity", "medium")



                    print(f"- [{severity.upper()}] {entity_name}: {description}")



    # Command: cards

    def do_cards(self, arg):

        """Show available cards of a specific type."""

        if not self.campaign_loaded:

            print("No campaign loaded. Use 'new' or 'load' first.")

            return



        # Parse arguments

        args = arg.strip().split()

        if not args:

            print("Usage: cards <type>")

            print("Available types: character, location, item, story, relationship")

            return



        card_type = args[0].lower()



        # Validate card type

        valid_types = ["character", "location", "item", "story", "relationship"]

        if card_type not in valid_types:

            print(f"Invalid card type: {card_type}")

            print(f"Available types: {', '.join(valid_types)}")

            return



        # Get cards of the specified type

        cards = self.memory_system.card_manager.get_cards_by_type(card_type)



        if not cards:

            print(f"No {card_type} cards found.")

            return



        print(f"\n=== {card_type.capitalize()} Cards ===")

        for card_id, card in cards.items():

            print(f"- {card.name} (ID: {card_id})")



    # Command: card

    def do_card(self, arg):

        """Show details of a specific card."""

        if not self.campaign_loaded:

            print("No campaign loaded. Use 'new' or 'load' first.")

            return



        # Parse arguments

        args = arg.strip().split()

        if not args:

            print("Usage: card <card_id>")

            return



        card_id = args[0]



        # Get card details

        details = self.memory_system.get_entity_details(card_id)



        if not details:

            print(f"Card not found: {card_id}")

            return



        entity = details["entity"]

        relationships = details["relationships"]

        memories = details["memories"]



        print(f"\n=== {entity['name']} ({entity['type'].capitalize()}) ===")

        print(f"ID: {entity['id']}")

        print(f"Description: {entity['description']}")



        # Print type-specific attributes

        if entity['type'] == "character":

            print(f"Status: {entity.get('status', 'Unknown')}")

            print(f"Location: {entity.get('location', 'Unknown')}")



            if 'traits' in entity:

                print("\nTraits:")

                for trait, value in entity['traits'].items():

                    print(f"- {trait}: {value}")



            if 'inventory' in entity and entity['inventory']:

                print("\nInventory:")

                for item in entity['inventory']:

                    print(f"- {item}")



        elif entity['type'] == "location":

            print(f"Region: {entity.get('region', 'Unknown')}")



            if 'features' in entity and entity['features']:

                print("\nFeatures:")

                for feature in entity['features']:

                    print(f"- {feature}")



            if 'inhabitants' in entity and entity['inhabitants']:

                print("\nInhabitants:")

                for inhabitant in entity['inhabitants']:

                    inhabitant_card = self.memory_system.card_manager.get_card(inhabitant)

                    name = inhabitant_card.name if inhabitant_card else inhabitant

                    print(f"- {name}")



        elif entity['type'] == "item":

            owner_id = entity.get('owner', '')

            owner = self.memory_system.card_manager.get_card(owner_id)

            owner_name = owner.name if owner else owner_id



            print(f"Owner: {owner_name if owner_id else 'None'}")



            loc_id = entity.get('location', '')

            loc = self.memory_system.card_manager.get_card(loc_id)

            loc_name = loc.name if loc else loc_id



            print(f"Location: {loc_name if loc_id else 'Unknown'}")



            if 'properties' in entity:

                print("\nProperties:")

                for prop, value in entity['properties'].items():

                    print(f"- {prop}: {value}")



        elif entity['type'] == "story":

            print(f"Status: {entity.get('status', 'Unknown')}")

            print(f"Type: {entity.get('plot_type', 'Unknown')}")



            if 'involved_characters' in entity and entity['involved_characters']:

                print("\nInvolved Characters:")

                for char_id in entity['involved_characters']:

                    char = self.memory_system.card_manager.get_card(char_id)

                    name = char.name if char else char_id

                    print(f"- {name}")



            if 'involved_locations' in entity and entity['involved_locations']:

                print("\nInvolved Locations:")

                for loc_id in entity['involved_locations']:

                    loc = self.memory_system.card_manager.get_card(loc_id)

                    name = loc.name if loc else loc_id

                    print(f"- {name}")



        # Print relationships

        if relationships:

            print("\nRelationships:")

            for rel in relationships:

                print(f"- With {rel['with']['name']}: {rel['type']} (Strength: {rel['strength']})")



        # Print memories

        if memories:

            print("\nRelevant Memories:")

            for i, memory in enumerate(memories[:5]):  # Show top 5 memories

                print(f"- {memory['text']}")



    # Command: exit

    def do_exit(self, arg):

        """Exit the program."""

        print("\nThank you for using the AI RPG Memory System. Goodbye!")

        return True



    # Command: quit (alias for exit)

    def do_quit(self, arg):

        """Exit the program."""

        return self.do_exit(arg)



    # Helper methods

    def _create_basic_setup(self) -> Dict[str, Any]:

        """Create a basic setup for a new campaign."""

        print("\nCreating a basic setup for your campaign...")



        # Ask for initial location name

        location_name = input("Initial location name (default: 'Town Square'): ")

        if not location_name:

            location_name = "Town Square"



        # Ask for character name

        character_name = input("Main character name (default: 'Adventurer'): ")

        if not character_name:

            character_name = "Adventurer"



        # Create basic setup

        return {

            "locations": [

                {

                    "name": location_name,

                    "description": f"The main gathering place in the area. {location_name} is bustling with activity.",

                    "region": "Starting Region",

                    "features": ["fountain", "market stalls", "cobblestone streets"],

                    "atmosphere": "lively"

                }

            ],

            "characters": [

                {

                    "name": character_name,

                    "description": f"A brave adventurer seeking fame and fortune.",

                    "status": "active",

                    "location": "0",  # Will be replaced with actual location ID

                    "traits": {

                        "strength": "average",

                        "intelligence": "average",

                        "charisma": "average"

                    },

                    "inventory": ["backpack", "map", "dagger"]

                }

            ],

            "stories": [

                {

                    "name": "The Beginning",

                    "description": "The start of a grand adventure.",

                    "status": "active",

                    "plot_type": "main"

                }

            ],

            "initial_focus": {

                "characters": ["0"],  # Will be replaced with actual character ID

                "location": "0",  # Will be replaced with actual location ID

                "items": []

            }

        }



    def _show_in_game_help(self) -> None:

        """Show in-game help."""

        print("\n=== In-Game Commands ===")

        print("/exit             - Return to main menu")

        print("/help             - Show this help")

        print("/status           - Show game status")

        print("/chars            - List all characters")

        print("/loc              - Show current location")

        print("/items            - List nearby items")

        print("/stories          - List active stories")

        print("/char <name>      - Show character details")

        print("/item <name>      - Show item details")

        print("/loc <name>       - Show location details")

        print("/story <name>     - Show story details")

        print("\nTo play, simply type what you want to say or do.\n")



    def _show_game_status(self) -> None:

        """Show the current game status."""

        summary = self.memory_system.get_campaign_summary()



        print("\n=== Game Status ===")



        if summary['current_location']:

            print(f"Current Location: {summary['current_location']['name']}")

            print(f"Description: {summary['current_location']['description']}")



        if summary['active_characters']:

            print("\nCharacters Present:")

            for char in summary['active_characters']:

                print(f"- {char['name']}: {char['description']}")



        if summary['active_stories']:

            print("\nActive Stories:")

            for story in summary['active_stories']:

                print(f"- {story['name']}: {story['description']}")



    def _show_characters(self) -> None:

        """Show all characters."""

        characters = self.memory_system.card_manager.get_cards_by_type("character")



        if not characters:

            print("No characters found.")

            return



        print("\n=== Characters ===")

        for char_id, character in characters.items():

            status = getattr(character, "status", "unknown")

            print(f"- {character.name} ({status})")



    def _show_location(self) -> None:

        """Show the current location."""

        if not self.memory_system.current_focus.get("location"):

            print("Current location unknown.")

            return



        location_id = self.memory_system.current_focus["location"]

        location = self.memory_system.card_manager.get_card(location_id)



        if not location:

            print("Current location unknown.")

            return



        print(f"\n=== Current Location: {location.name} ===")

        print(f"Description: {location.description}")



        if hasattr(location, "features") and location.features:

            print("\nFeatures:")

            for feature in location.features:

                print(f"- {feature}")



        # Characters at this location

        characters_at_location = []

        for character in self.memory_system.card_manager.cards_by_type.get("character", {}).values():

            if hasattr(character, "location") and character.location == location_id:

                characters_at_location.append(character)



        if characters_at_location:

            print("\nCharacters Present:")

            for character in characters_at_location:

                print(f"- {character.name}")



        # Items at this location

        items_at_location = []

        for item in self.memory_system.card_manager.cards_by_type.get("item", {}).values():

            if hasattr(item, "location") and item.location == location_id:

                items_at_location.append(item)



        if items_at_location:

            print("\nItems Present:")

            for item in items_at_location:

                print(f"- {item.name}")



    def _show_items(self) -> None:

        """Show nearby items."""

        location_id = self.memory_system.current_focus.get("location")

        if not location_id:

            print("Current location unknown.")

            return



        # Items at this location

        items_at_location = []

        for item in self.memory_system.card_manager.cards_by_type.get("item", {}).values():

            if hasattr(item, "location") and item.location == location_id:

                items_at_location.append(item)



        if not items_at_location:

            print("No items found nearby.")

            return



        print("\n=== Nearby Items ===")

        for item in items_at_location:

            print(f"- {item.name}: {item.description}")



    def _show_stories(self) -> None:

        """Show active stories."""

        active_stories = self.memory_system.card_manager.get_active_stories()



        if not active_stories:

            print("No active stories found.")

            return



        print("\n=== Active Stories ===")

        for story in active_stories:

            print(f"- {story.name}: {story.description}")



    def _show_character_details(self, name_or_id: str) -> None:

        """Show details of a specific character."""

        # Try to find character by ID first

        character = self.memory_system.card_manager.get_card(name_or_id)



        if not character or character.type != "character":

            # Try to find by name

            characters = self.memory_system.card_manager.find_cards_by_name(name_or_id, "character")



            if not characters:

                print(f"Character not found: {name_or_id}")

                return



            character = characters[0]



        details = self.memory_system.get_entity_details(character.id)

        entity = details["entity"]



        print(f"\n=== Character: {entity['name']} ===")

        print(f"Description: {entity['description']}")

        print(f"Status: {entity.get('status', 'Unknown')}")



        location_id = entity.get('location', '')

        location = self.memory_system.card_manager.get_card(location_id)

        location_name = location.name if location else location_id



        print(f"Location: {location_name if location_id else 'Unknown'}")



        if 'traits' in entity and entity['traits']:

            print("\nTraits:")

            for trait, value in entity['traits'].items():

                print(f"- {trait}: {value}")



        if 'inventory' in entity and entity['inventory']:

            print("\nInventory:")

            for item in entity['inventory']:

                print(f"- {item}")



        relationships = details["relationships"]

        if relationships:

            print("\nRelationships:")

            for rel in relationships:

                print(f"- With {rel['with']['name']}: {rel['type']} (Strength: {rel['strength']})")



    def _show_item_details(self, name_or_id: str) -> None:

        """Show details of a specific item."""

        # Try to find item by ID first

        item = self.memory_system.card_manager.get_card(name_or_id)



        if not item or item.type != "item":

            # Try to find by name

            items = self.memory_system.card_manager.find_cards_by_name(name_or_id, "item")



            if not items:

                print(f"Item not found: {name_or_id}")

                return



            item = items[0]



        details = self.memory_system.get_entity_details(item.id)

        entity = details["entity"]



        print(f"\n=== Item: {entity['name']} ===")

        print(f"Description: {entity['description']}")



        owner_id = entity.get('owner', '')

        owner = self.memory_system.card_manager.get_card(owner_id)

        owner_name = owner.name if owner else owner_id



        print(f"Owner: {owner_name if owner_id else 'None'}")



        location_id = entity.get('location', '')

        location = self.memory_system.card_manager.get_card(location_id)

        location_name = location.name if location else location_id



        print(f"Location: {location_name if location_id else 'Unknown'}")



        if 'properties' in entity and entity['properties']:

            print("\nProperties:")

            for prop, value in entity['properties'].items():

                print(f"- {prop}: {value}")



        if 'effects' in entity and entity['effects']:

            print("\nEffects:")

            for effect in entity['effects']:

                print(f"- {effect}")



    def _show_location_details(self, name_or_id: str) -> None:

        """Show details of a specific location."""

        # Try to find location by ID first

        location = self.memory_system.card_manager.get_card(name_or_id)



        if not location or location.type != "location":

            # Try to find by name

            locations = self.memory_system.card_manager.find_cards_by_name(name_or_id, "location")



            if not locations:

                print(f"Location not found: {name_or_id}")

                return



            location = locations[0]



        details = self.memory_system.get_entity_details(location.id)

        entity = details["entity"]



        print(f"\n=== Location: {entity['name']} ===")

        print(f"Description: {entity['description']}")

        print(f"Region: {entity.get('region', 'Unknown')}")



        if 'features' in entity and entity['features']:

            print("\nFeatures:")

            for feature in entity['features']:

                print(f"- {feature}")



        if 'atmosphere' in entity:

            print(f"Atmosphere: {entity['atmosphere']}")



        # Characters at this location

        characters_at_location = []

        for character in self.memory_system.card_manager.cards_by_type.get("character", {}).values():

            if hasattr(character, "location") and character.location == location.id:

                characters_at_location.append(character)



        if characters_at_location:

            print("\nCharacters Present:")

            for character in characters_at_location:

                print(f"- {character.name}")



        # Items at this location

        items_at_location = []

        for item in self.memory_system.card_manager.cards_by_type.get("item", {}).values():

            if hasattr(item, "location") and item.location == location.id:

                items_at_location.append(item)



        if items_at_location:

            print("\nItems Present:")

            for item in items_at_location:

                print(f"- {item.name}")



    def _show_story_details(self, name_or_id: str) -> None:

        """Show details of a specific story."""

        # Try to find story by ID first

        story = self.memory_system.card_manager.get_card(name_or_id)



        if not story or story.type != "story":

            # Try to find by name

            stories = self.memory_system.card_manager.find_cards_by_name(name_or_id, "story")



            if not stories:

                print(f"Story not found: {name_or_id}")

                return



            story = stories[0]



        details = self.memory_system.get_entity_details(story.id)

        entity = details["entity"]



        print(f"\n=== Story: {entity['name']} ===")

        print(f"Description: {entity['description']}")

        print(f"Status: {entity.get('status', 'Unknown')}")

        print(f"Type: {entity.get('plot_type', 'Unknown')}")



        if 'involved_characters' in entity and entity['involved_characters']:

            print("\nInvolved Characters:")

            for char_id in entity['involved_characters']:

                char = self.memory_system.card_manager.get_card(char_id)

                name = char.name if char else char_id

                print(f"- {name}")



        if 'involved_locations' in entity and entity['involved_locations']:

            print("\nInvolved Locations:")

            for loc_id in entity['involved_locations']:

                loc = self.memory_system.card_manager.get_card(loc_id)

                name = loc.name if loc else loc_id

                print(f"- {name}")



        if 'timeline' in entity and entity['timeline']:

            print("\nTimeline:")

            for event in entity['timeline']:

                print(f"- {event}")