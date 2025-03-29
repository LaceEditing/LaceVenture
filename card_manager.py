"""
Manages entity cards (characters, locations, items, etc.) for the RPG memory system.
"""

import os
import uuid
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from config import DATA_DIR, CAMPAIGNS_DIR

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Base class for all cards
class BaseCard:
    """
    Base class for all entity cards in the system.
    """

    def __init__(self, card_id: str, card_type: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize a card.

        Args:
            card_id: Unique identifier for the card
            card_type: Type of card (character, location, etc.)
            name: Name of the entity
            initial_data: Initial data for the card
        """
        self.id = card_id
        self.type = card_type
        self.name = name
        self.creation_time = time.time()
        self.last_modified = self.creation_time
        self.description = initial_data.get("description", "") if initial_data else ""
        self.history = []

        # Add initial data as first history entry
        if initial_data:
            self.update({
                "description": self.description,
                **{k: v for k, v in initial_data.items() if k != "description"}
            }, "initial_creation")

    def update(self, changes: Dict[str, Any], source: str) -> None:
        """
        Update the card with new information.

        Args:
            changes: Changes to apply to the card
            source: Source of the changes (e.g., "game_event", "user_edit")
        """
        # Apply changes
        for key, value in changes.items():
            if key != "id" and key != "type" and key != "history" and hasattr(self, key):
                setattr(self, key, value)

        # Update modification time
        self.last_modified = time.time()

        # Add to history
        self.history.append({
            "timestamp": self.last_modified,
            "changes": changes.copy(),
            "source": source
        })

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the card to a dictionary.

        Returns:
            Dictionary representation of the card
        """
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "creation_time": self.creation_time,
            "last_modified": self.last_modified,
            "description": self.description,
            "history": self.history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseCard':
        """
        Create a card from a dictionary.

        Args:
            data: Dictionary representation of the card

        Returns:
            A new card instance
        """
        card = cls(data["id"], data["type"], data["name"])
        card.creation_time = data.get("creation_time", time.time())
        card.last_modified = data.get("last_modified", card.creation_time)
        card.description = data.get("description", "")
        card.history = data.get("history", [])

        # Set additional attributes based on card type
        for key, value in data.items():
            if key not in ["id", "type", "name", "creation_time", "last_modified", "description", "history"]:
                setattr(card, key, value)

        return card


class CharacterCard(BaseCard):
    """
    Card for character entities.
    """

    def __init__(self, card_id: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize a character card.

        Args:
            card_id: Unique identifier for the card
            name: Name of the character
            initial_data: Initial data for the card
        """
        super().__init__(card_id, "character", name, initial_data)

        # Character-specific attributes
        self.traits = initial_data.get("traits", {}) if initial_data else {}
        self.inventory = initial_data.get("inventory", []) if initial_data else []
        self.stats = initial_data.get("stats", {}) if initial_data else {}
        self.relationships = initial_data.get("relationships", {}) if initial_data else {}
        self.location = initial_data.get("location", "unknown") if initial_data else "unknown"
        self.status = initial_data.get("status", "active") if initial_data else "active"
        self.backstory = initial_data.get("backstory", "") if initial_data else ""
        self.appearance = initial_data.get("appearance", "") if initial_data else ""
        self.goals = initial_data.get("goals", []) if initial_data else []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the character card to a dictionary.

        Returns:
            Dictionary representation of the character card
        """
        base_dict = super().to_dict()

        # Add character-specific attributes
        character_dict = {
            "traits": self.traits,
            "inventory": self.inventory,
            "stats": self.stats,
            "relationships": self.relationships,
            "location": self.location,
            "status": self.status,
            "backstory": self.backstory,
            "appearance": self.appearance,
            "goals": self.goals
        }

        return {**base_dict, **character_dict}


class LocationCard(BaseCard):
    """
    Card for location entities.
    """

    def __init__(self, card_id: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize a location card.

        Args:
            card_id: Unique identifier for the card
            name: Name of the location
            initial_data: Initial data for the card
        """
        super().__init__(card_id, "location", name, initial_data)

        # Location-specific attributes
        self.region = initial_data.get("region", "") if initial_data else ""
        self.features = initial_data.get("features", []) if initial_data else []
        self.inhabitants = initial_data.get("inhabitants", []) if initial_data else []
        self.items = initial_data.get("items", []) if initial_data else []
        self.connections = initial_data.get("connections", {}) if initial_data else {}
        self.atmosphere = initial_data.get("atmosphere", "") if initial_data else ""
        self.events = initial_data.get("events", []) if initial_data else []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the location card to a dictionary.

        Returns:
            Dictionary representation of the location card
        """
        base_dict = super().to_dict()

        # Add location-specific attributes
        location_dict = {
            "region": self.region,
            "features": self.features,
            "inhabitants": self.inhabitants,
            "items": self.items,
            "connections": self.connections,
            "atmosphere": self.atmosphere,
            "events": self.events
        }

        return {**base_dict, **location_dict}


class ItemCard(BaseCard):
    """
    Card for item entities.
    """

    def __init__(self, card_id: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize an item card.

        Args:
            card_id: Unique identifier for the card
            name: Name of the item
            initial_data: Initial data for the card
        """
        super().__init__(card_id, "item", name, initial_data)

        # Item-specific attributes
        self.properties = initial_data.get("properties", {}) if initial_data else {}
        self.owner = initial_data.get("owner", "") if initial_data else ""
        self.location = initial_data.get("location", "") if initial_data else ""
        self.effects = initial_data.get("effects", []) if initial_data else []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the item card to a dictionary.

        Returns:
            Dictionary representation of the item card
        """
        base_dict = super().to_dict()

        # Add item-specific attributes
        item_dict = {
            "properties": self.properties,
            "owner": self.owner,
            "location": self.location,
            "effects": self.effects
        }

        return {**base_dict, **item_dict}


class StoryCard(BaseCard):
    """
    Card for story elements (plot points, quests, etc.).
    """

    def __init__(self, card_id: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize a story card.

        Args:
            card_id: Unique identifier for the card
            name: Name of the story element
            initial_data: Initial data for the card
        """
        super().__init__(card_id, "story", name, initial_data)

        # Story-specific attributes
        self.plot_type = initial_data.get("plot_type",
                                          "main") if initial_data else "main"  # main, side, character, etc.
        self.status = initial_data.get("status",
                                       "active") if initial_data else "active"  # active, completed, failed, etc.
        self.involved_characters = initial_data.get("involved_characters", []) if initial_data else []
        self.involved_locations = initial_data.get("involved_locations", []) if initial_data else []
        self.involved_items = initial_data.get("involved_items", []) if initial_data else []
        self.prerequisites = initial_data.get("prerequisites", []) if initial_data else []
        self.outcomes = initial_data.get("outcomes", []) if initial_data else []
        self.timeline = initial_data.get("timeline", []) if initial_data else []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the story card to a dictionary.

        Returns:
            Dictionary representation of the story card
        """
        base_dict = super().to_dict()

        # Add story-specific attributes
        story_dict = {
            "plot_type": self.plot_type,
            "status": self.status,
            "involved_characters": self.involved_characters,
            "involved_locations": self.involved_locations,
            "involved_items": self.involved_items,
            "prerequisites": self.prerequisites,
            "outcomes": self.outcomes,
            "timeline": self.timeline
        }

        return {**base_dict, **story_dict}


class RelationshipCard(BaseCard):
    """
    Card for relationships between entities.
    """

    def __init__(self, card_id: str, name: str, initial_data: Dict[str, Any] = None):
        """
        Initialize a relationship card.

        Args:
            card_id: Unique identifier for the card
            name: Name of the relationship
            initial_data: Initial data for the card
        """
        super().__init__(card_id, "relationship", name, initial_data)

        # Relationship-specific attributes
        self.entity1 = initial_data.get("entity1", "") if initial_data else ""
        self.entity2 = initial_data.get("entity2", "") if initial_data else ""
        self.relationship_type = initial_data.get("relationship_type", "") if initial_data else ""
        self.strength = initial_data.get("strength", 0) if initial_data else 0
        self.emotions = initial_data.get("emotions", {}) if initial_data else {}
        self.events = initial_data.get("events", []) if initial_data else []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the relationship card to a dictionary.

        Returns:
            Dictionary representation of the relationship card
        """
        base_dict = super().to_dict()

        # Add relationship-specific attributes
        relationship_dict = {
            "entity1": self.entity1,
            "entity2": self.entity2,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "emotions": self.emotions,
            "events": self.events
        }

        return {**base_dict, **relationship_dict}


class CardManager:
    """
    Manages all entity cards for a campaign.
    """

    def __init__(self, campaign_id: str):
        """
        Initialize the card manager.

        Args:
            campaign_id: Unique identifier for the campaign
        """
        self.campaign_id = campaign_id
        self.campaign_dir = os.path.join(CAMPAIGNS_DIR, campaign_id)
        self.cards_dir = os.path.join(self.campaign_dir, "cards")

        # Create directories if they don't exist
        os.makedirs(self.cards_dir, exist_ok=True)

        # Initialize card collections
        self.cards: Dict[str, BaseCard] = {}
        self.cards_by_type: Dict[str, Dict[str, BaseCard]] = {
            "character": {},
            "location": {},
            "item": {},
            "story": {},
            "relationship": {}
        }

        # Load existing cards
        self.load_cards()

    def load_cards(self) -> None:
        """
        Load all cards from disk.
        """
        for card_type in self.cards_by_type.keys():
            type_dir = os.path.join(self.cards_dir, card_type)
            os.makedirs(type_dir, exist_ok=True)

            for filename in os.listdir(type_dir):
                if filename.endswith(".json"):
                    card_path = os.path.join(type_dir, filename)
                    card_id = filename[:-5]  # Remove .json extension

                    try:
                        with open(card_path, "r") as f:
                            card_data = json.load(f)

                            # Fix for string data - try to parse it if it's a string
                            if isinstance(card_data, str):
                                try:
                                    # Attempt to parse the string as JSON
                                    card_data = json.loads(card_data)
                                    # Save the fixed data back to the file
                                    with open(card_path, "w") as fix_file:
                                        json.dump(card_data, fix_file, indent=2)
                                    logger.info(f"Fixed string card data for {card_id}")
                                except json.JSONDecodeError:
                                    logger.error(f"Card data for {card_id} is a string and could not be parsed")
                                    continue

                            # Safety check: ensure card_data is a dictionary
                            if isinstance(card_data, dict):
                                self.create_card_from_dict(card_data)
                            else:
                                logger.error(f"Card data for {card_id} is not a dictionary: {type(card_data)}")
                    except Exception as e:
                        logger.error(f"Error loading card {card_id}: {e}")


    def create_card(self, card_type: str, name: str, initial_data: Dict[str, Any] = None) -> str:
        """
        Create a new card.

        Args:
            card_type: Type of card to create
            name: Name of the entity
            initial_data: Initial data for the card

        Returns:
            ID of the created card
        """
        card_id = str(uuid.uuid4())

        if initial_data is None:
            initial_data = {}

        # Create appropriate card type
        if card_type == "character":
            card = CharacterCard(card_id, name, initial_data)
        elif card_type == "location":
            card = LocationCard(card_id, name, initial_data)
        elif card_type == "item":
            card = ItemCard(card_id, name, initial_data)
        elif card_type == "story":
            card = StoryCard(card_id, name, initial_data)
        elif card_type == "relationship":
            card = RelationshipCard(card_id, name, initial_data)
        else:
            raise ValueError(f"Unsupported card type: {card_type}")

        # Add card to collections
        self.cards[card_id] = card
        self.cards_by_type[card_type][card_id] = card

        # Save card to disk
        self.save_card(card)

        logger.info(f"Created {card_type} card: {name} ({card_id})")
        return card_id

    def create_card_from_dict(self, card_data: Dict[str, Any]) -> str:
        """
        Create a card from a dictionary.

        Args:
            card_data: Dictionary representation of the card

        Returns:
            ID of the created card
        """
        card_type = card_data["type"]
        card_id = card_data["id"]

        # Create appropriate card type
        if card_type == "character":
            card = CharacterCard.from_dict(card_data)
        elif card_type == "location":
            card = LocationCard.from_dict(card_data)
        elif card_type == "item":
            card = ItemCard.from_dict(card_data)
        elif card_type == "story":
            card = StoryCard.from_dict(card_data)
        elif card_type == "relationship":
            card = RelationshipCard.from_dict(card_data)
        else:
            raise ValueError(f"Unsupported card type: {card_type}")

        # Add card to collections
        self.cards[card_id] = card
        self.cards_by_type[card_type][card_id] = card

        return card_id

    def get_card(self, card_id: str) -> Optional[BaseCard]:
        """
        Get a card by ID.

        Args:
            card_id: ID of the card to get

        Returns:
            The card, or None if not found
        """
        return self.cards.get(card_id)

    def get_cards_by_type(self, card_type: str) -> Dict[str, BaseCard]:
        """
        Get all cards of a specific type.

        Args:
            card_type: Type of cards to get

        Returns:
            Dictionary of cards of the specified type
        """
        return self.cards_by_type.get(card_type, {})

    def update_card(self, card_id: str, changes: Dict[str, Any], source: str) -> bool:
        """
        Update a card.

        Args:
            card_id: ID of the card to update
            changes: Changes to apply to the card
            source: Source of the changes

        Returns:
            True if successful
        """
        card = self.get_card(card_id)
        if card is None:
            logger.error(f"Card not found: {card_id}")
            return False

        # Apply changes
        card.update(changes, source)

        # Save card to disk
        self.save_card(card)

        logger.info(f"Updated card: {card_id}")
        return True

    def save_card(self, card: BaseCard) -> None:
        """
        Save a card to disk with improved robustness.

        Args:
            card: Card to save
        """
        type_dir = os.path.join(self.cards_dir, card.type)
        os.makedirs(type_dir, exist_ok=True)

        card_path = os.path.join(type_dir, f"{card.id}.json")

        try:
            # Get dictionary representation of the card
            card_dict = card.to_dict()

            # Validate that it's a proper dictionary
            if not isinstance(card_dict, dict):
                logger.error(f"Card {card.id} to_dict() did not return a dictionary")
                return

            # Save to disk with backups
            temp_path = card_path + ".temp"
            with open(temp_path, "w") as f:
                json.dump(card_dict, f, indent=2)

            # Only replace original file if temp save succeeded
            if os.path.exists(temp_path):
                # Backup existing file if it exists
                if os.path.exists(card_path):
                    backup_path = card_path + ".bak"
                    try:
                        os.replace(card_path, backup_path)
                    except Exception as backup_error:
                        logger.warning(f"Could not create backup of card {card.id}: {backup_error}")

                # Replace with new file
                os.replace(temp_path, card_path)
                logger.info(f"Saved card {card.id} successfully")
        except Exception as e:
            logger.error(f"Error saving card {card.id}: {e}")

    def delete_card(self, card_id: str) -> bool:
        """
        Delete a card.

        Args:
            card_id: ID of the card to delete

        Returns:
            True if successful
        """
        card = self.get_card(card_id)
        if card is None:
            logger.error(f"Card not found: {card_id}")
            return False

        # Remove card from collections
        self.cards.pop(card_id)
        self.cards_by_type[card.type].pop(card_id)

        # Delete card file
        type_dir = os.path.join(self.cards_dir, card.type)
        card_path = os.path.join(type_dir, f"{card_id}.json")

        try:
            if os.path.exists(card_path):
                os.remove(card_path)
        except Exception as e:
            logger.error(f"Error deleting card file {card_id}: {e}")

        logger.info(f"Deleted card: {card_id}")
        return True

    def find_cards_by_name(self, name: str, card_type: Optional[str] = None) -> List[BaseCard]:
        """
        Find cards by name.

        Args:
            name: Name to search for
            card_type: Type of cards to search (or None for all types)

        Returns:
            List of matching cards
        """
        results = []

        if card_type:
            # Search only specified type
            for card in self.cards_by_type.get(card_type, {}).values():
                if name.lower() in card.name.lower():
                    results.append(card)
        else:
            # Search all types
            for card in self.cards.values():
                if name.lower() in card.name.lower():
                    results.append(card)

        return results

    def get_character_at_location(self, location_id: str) -> List[CharacterCard]:
        """
        Get all characters at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of characters at the location
        """
        results = []

        for card in self.cards_by_type.get("character", {}).values():
            if card.location == location_id:
                results.append(card)

        return results

    def get_relationships_for_entity(self, entity_id: str) -> List[RelationshipCard]:
        """
        Get all relationships involving a specific entity.

        Args:
            entity_id: ID of the entity

        Returns:
            List of relationships involving the entity
        """
        results = []

        for card in self.cards_by_type.get("relationship", {}).values():
            if card.entity1 == entity_id or card.entity2 == entity_id:
                results.append(card)

        return results

    def get_items_owned_by(self, character_id: str) -> List[ItemCard]:
        """
        Get all items owned by a specific character.

        Args:
            character_id: ID of the character

        Returns:
            List of items owned by the character
        """
        results = []

        for card in self.cards_by_type.get("item", {}).values():
            if card.owner == character_id:
                results.append(card)

        return results

    def get_active_stories(self) -> List[StoryCard]:
        """
        Get all active story elements.

        Returns:
            List of active story elements
        """
        results = []

        for card in self.cards_by_type.get("story", {}).values():
            if card.status == "active":
                results.append(card)

        return results

    def create_or_update_relationship(self, entity1_id: str, entity2_id: str,
                                      relationship_type: str, strength: int,
                                      emotions: Dict[str, int] = None,
                                      source: str = "game_event") -> str:
        """
        Create or update a relationship between two entities.

        Args:
            entity1_id: ID of the first entity
            entity2_id: ID of the second entity
            relationship_type: Type of relationship
            strength: Strength of the relationship (1-10)
            emotions: Emotional components of the relationship
            source: Source of the changes

        Returns:
            ID of the relationship card
        """
        # Check if entities exist
        entity1 = self.get_card(entity1_id)
        entity2 = self.get_card(entity2_id)

        if entity1 is None or entity2 is None:
            logger.error(f"One or both entities not found: {entity1_id}, {entity2_id}")
            return None

        # Ensure entity order is consistent (alphabetical by ID)
        if entity1_id > entity2_id:
            entity1_id, entity2_id = entity2_id, entity1_id

        # Try to find existing relationship
        for card in self.cards_by_type.get("relationship", {}).values():
            if card.entity1 == entity1_id and card.entity2 == entity2_id:
                # Update existing relationship
                changes = {
                    "relationship_type": relationship_type,
                    "strength": strength
                }

                if emotions:
                    changes["emotions"] = emotions

                self.update_card(card.id, changes, source)
                return card.id

        # Create new relationship
        name = f"{entity1.name} and {entity2.name}"

        if emotions is None:
            emotions = {}

        initial_data = {
            "entity1": entity1_id,
            "entity2": entity2_id,
            "relationship_type": relationship_type,
            "strength": strength,
            "emotions": emotions,
            "events": [{
                "timestamp": time.time(),
                "description": f"Relationship established: {relationship_type}",
                "source": source
            }]
        }

        return self.create_card("relationship", name, initial_data)

    def get_card_summary(self, card_id: str) -> str:
        """
        Get a summary of a card.

        Args:
            card_id: ID of the card

        Returns:
            Summary string
        """
        card = self.get_card(card_id)
        if card is None:
            return "Card not found"

        if card.type == "character":
            return self._get_character_summary(card)
        elif card.type == "location":
            return self._get_location_summary(card)
        elif card.type == "item":
            return self._get_item_summary(card)
        elif card.type == "story":
            return self._get_story_summary(card)
        elif card.type == "relationship":
            return self._get_relationship_summary(card)
        else:
            return f"{card.name}: {card.description}"

    def _get_character_summary(self, card: CharacterCard) -> str:
        """Generate a summary for a character card."""
        traits_str = ", ".join(f"{k}: {v}" for k, v in card.traits.items())
        inventory_str = ", ".join(card.inventory) if card.inventory else "None"

        return (
            f"Character: {card.name}\n"
            f"Description: {card.description}\n"
            f"Traits: {traits_str}\n"
            f"Inventory: {inventory_str}\n"
            f"Location: {card.location}\n"
            f"Status: {card.status}"
        )

    def _get_location_summary(self, card: LocationCard) -> str:
        """Generate a summary for a location card."""
        features_str = ", ".join(card.features) if card.features else "None"
        inhabitants_str = ", ".join(card.inhabitants) if card.inhabitants else "None"

        return (
            f"Location: {card.name}\n"
            f"Description: {card.description}\n"
            f"Region: {card.region}\n"
            f"Features: {features_str}\n"
            f"Inhabitants: {inhabitants_str}\n"
            f"Atmosphere: {card.atmosphere}"
        )

    def _get_item_summary(self, card: ItemCard) -> str:
        """Generate a summary for an item card."""
        properties_str = ", ".join(f"{k}: {v}" for k, v in card.properties.items())
        effects_str = ", ".join(card.effects) if card.effects else "None"

        return (
            f"Item: {card.name}\n"
            f"Description: {card.description}\n"
            f"Properties: {properties_str}\n"
            f"Owner: {card.owner}\n"
            f"Location: {card.location}\n"
            f"Effects: {effects_str}"
        )

    def _get_story_summary(self, card: StoryCard) -> str:
        """Generate a summary for a story card."""
        characters_str = ", ".join(card.involved_characters) if card.involved_characters else "None"
        locations_str = ", ".join(card.involved_locations) if card.involved_locations else "None"

        return (
            f"Story: {card.name}\n"
            f"Description: {card.description}\n"
            f"Type: {card.plot_type}\n"
            f"Status: {card.status}\n"
            f"Characters: {characters_str}\n"
            f"Locations: {locations_str}"
        )

    def _get_relationship_summary(self, card: RelationshipCard) -> str:
        """Generate a summary for a relationship card."""
        emotions_str = ", ".join(f"{k}: {v}" for k, v in card.emotions.items())

        entity1 = self.get_card(card.entity1)
        entity2 = self.get_card(card.entity2)

        entity1_name = entity1.name if entity1 else card.entity1
        entity2_name = entity2.name if entity2 else card.entity2

        return (
            f"Relationship: {card.name}\n"
            f"Between: {entity1_name} and {entity2_name}\n"
            f"Type: {card.relationship_type}\n"
            f"Strength: {card.strength}/10\n"
            f"Emotions: {emotions_str}\n"
            f"Description: {card.description}"
        )