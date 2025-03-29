"""
Extracts structured information from game text.
"""

import re
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Set

from llm_interface import LLMInterface
from card_manager import CardManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InformationExtractor:
    """
    Extracts structured information from game text using the LLM.
    """

    def __init__(self, llm_interface: LLMInterface, card_manager: CardManager):
        """
        Initialize the information extractor.

        Args:
            llm_interface: Interface to the language model
            card_manager: Card manager instance
        """
        self.llm = llm_interface
        self.card_manager = card_manager

        # Precompute entity names for efficient extraction
        self.entity_names = {}
        self.entity_ids = {}
        self._precompute_entity_data()

    def _precompute_entity_data(self) -> None:
        """
        Precompute entity names and IDs for efficient extraction.
        """
        for card_type in ["character", "location", "item"]:
            self.entity_names[card_type] = {}
            self.entity_ids[card_type] = {}

            for card_id, card in self.card_manager.cards_by_type.get(card_type, {}).items():
                name_lower = card.name.lower()
                self.entity_names[card_type][card_id] = card.name
                self.entity_ids[card_type][name_lower] = card_id

    def refresh_entity_data(self) -> None:
        """
        Refresh entity names and IDs. Should be called when cards are added or removed.
        """
        self._precompute_entity_data()

    def extract_information(self, user_input: str, ai_response: str, current_context: str) -> Dict[str, Any]:
        """
        Extract structured information from game text.

        Args:
            user_input: User's text input
            ai_response: AI's response
            current_context: Current game context

        Returns:
            Structured information
        """
        # Create a prompt for the LLM to extract structured data
        extraction_prompt = self._create_extraction_prompt(user_input, ai_response, current_context)

        # Extract structured data using the LLM
        try:
            extracted_data = self.llm.extract_structured_data(extraction_prompt)

            # Process and validate the extracted data
            processed_data = self._process_extracted_data(extracted_data)

            return processed_data
        except Exception as e:
            logger.error(f"Error extracting information: {e}")
            return {}

    def _create_extraction_prompt(self, user_input: str, ai_response: str, current_context: str) -> str:
        """
        Create a prompt for the LLM to extract structured data.

        Args:
            user_input: User's text input
            ai_response: AI's response
            current_context: Current game context

        Returns:
            Extraction prompt
        """
        # Create a list of known entities to help with extraction
        known_entities = self._get_known_entities_text()

        prompt = f"""
        As an RPG game assistant, analyze the following interaction and extract all factual changes in a structured format.

        USER INPUT:
        {user_input}

        AI RESPONSE:
        {ai_response}

        KNOWN ENTITIES:
        {known_entities}

        EXTRACTION INSTRUCTIONS:
        Extract changes to characters, locations, items, relationships, and story elements.
        Be precise and factual - only extract information that is explicitly stated or clearly implied.
        Categorize each change by type and provide entity IDs where possible.

        YOUR RESPONSE SHOULD BE IN THE FOLLOWING JSON FORMAT:
        {{
            "character_changes": [
                {{
                    "character_id": "ID or name if new",
                    "is_new": true/false,
                    "name": "Only if new character",
                    "changes": {{
                        "description": "Any changes to description",
                        "traits": {{"trait_name": "value"}},
                        "inventory": ["added_item1", "added_item2"],
                        "inventory_removed": ["removed_item1"],
                        "location": "location_id or name",
                        "status": "Any status change",
                        "relationships": {{"target_id": {{"type": "relationship_type", "strength": 1-10}}}}
                    }}
                }}
            ],
            "location_changes": [
                {{
                    "location_id": "ID or name if new",
                    "is_new": true/false,
                    "name": "Only if new location",
                    "changes": {{
                        "description": "Any changes to description",
                        "features": ["feature1", "feature2"],
                        "atmosphere": "Any atmosphere changes",
                        "inhabitants": ["character_id1", "character_id2"],
                        "items": ["item_id1", "item_id2"]
                    }}
                }}
            ],
            "item_changes": [
                {{
                    "item_id": "ID or name if new",
                    "is_new": true/false,
                    "name": "Only if new item",
                    "changes": {{
                        "description": "Any changes to description",
                        "properties": {{"property_name": "value"}},
                        "owner": "character_id or name",
                        "location": "location_id or name"
                    }}
                }}
            ],
            "relationship_changes": [
                {{
                    "entity1_id": "ID or name",
                    "entity2_id": "ID or name",
                    "relationship_type": "Type of relationship",
                    "strength": 1-10,
                    "emotions": {{"emotion_name": 1-10}}
                }}
            ],
            "story_developments": [
                {{
                    "story_id": "ID or name if new",
                    "is_new": true/false,
                    "name": "Only if new story element",
                    "changes": {{
                        "description": "Any changes to story",
                        "status": "active/completed/failed",
                        "involved_characters": ["character_id1", "character_id2"],
                        "involved_locations": ["location_id1", "location_id2"]
                    }}
                }}
            ],
            "current_focus": {{
                "characters": ["IDs of characters currently in scene"],
                "location": "ID of current location",
                "items": ["IDs of items currently in scene"]
            }}
        }}

        ONLY EXTRACT FACTUAL INFORMATION, NOT SPECULATION OR POSSIBILITIES.
        """

        return prompt

    def _get_known_entities_text(self) -> str:
        """
        Get a formatted text of known entities to include in the extraction prompt.

        Returns:
            Formatted text of known entities
        """
        entity_text = ""

        # Add characters
        entity_text += "CHARACTERS:\n"
        for card_id, name in self.entity_names.get("character", {}).items():
            entity_text += f"- {name} (ID: {card_id})\n"

        # Add locations
        entity_text += "\nLOCATIONS:\n"
        for card_id, name in self.entity_names.get("location", {}).items():
            entity_text += f"- {name} (ID: {card_id})\n"

        # Add items
        entity_text += "\nITEMS:\n"
        for card_id, name in self.entity_names.get("item", {}).items():
            entity_text += f"- {name} (ID: {card_id})\n"

        # Add active stories
        entity_text += "\nACTIVE STORIES:\n"
        for story in self.card_manager.get_active_stories():
            entity_text += f"- {story.name} (ID: {story.id})\n"

        return entity_text

    def _process_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate the extracted data.

        Args:
            extracted_data: Raw extracted data from the LLM

        Returns:
            Processed data
        """
        processed_data = {
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

        # Process character changes
        for char_change in extracted_data.get("character_changes", []):
            processed_char = self._process_character_change(char_change)
            if processed_char:
                processed_data["character_changes"].append(processed_char)

        # Process location changes
        for loc_change in extracted_data.get("location_changes", []):
            processed_loc = self._process_location_change(loc_change)
            if processed_loc:
                processed_data["location_changes"].append(processed_loc)

        # Process item changes
        for item_change in extracted_data.get("item_changes", []):
            processed_item = self._process_item_change(item_change)
            if processed_item:
                processed_data["item_changes"].append(processed_item)

        # Process relationship changes
        for rel_change in extracted_data.get("relationship_changes", []):
            processed_rel = self._process_relationship_change(rel_change)
            if processed_rel:
                processed_data["relationship_changes"].append(processed_rel)

        # Process story developments
        for story_change in extracted_data.get("story_developments", []):
            processed_story = self._process_story_change(story_change)
            if processed_story:
                processed_data["story_developments"].append(processed_story)

        # Process current focus
        if "current_focus" in extracted_data:
            processed_data["current_focus"] = self._process_current_focus(extracted_data["current_focus"])

        # Add timestamp
        processed_data["timestamp"] = time.time()

        return processed_data

    def _process_character_change(self, char_change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a character change.

        Args:
            char_change: Character change data

        Returns:
            Processed character change, or None if invalid
        """
        # Get character ID or name
        character_id = char_change.get("character_id")
        is_new = char_change.get("is_new", False)

        # Validate character ID for existing characters
        if not is_new and character_id:
            # Try to resolve by name if not an ID
            if character_id not in self.card_manager.cards_by_type.get("character", {}):
                character_id_lower = character_id.lower()
                if character_id_lower in self.entity_ids.get("character", {}):
                    character_id = self.entity_ids["character"][character_id_lower]
                else:
                    # Character not found, treat as new
                    is_new = True

        # Process changes
        changes = char_change.get("changes", {})

        # Return processed character change
        return {
            "character_id": character_id,
            "is_new": is_new,
            "name": char_change.get("name", character_id) if is_new else None,
            "changes": changes
        }

    def _process_location_change(self, loc_change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a location change.

        Args:
            loc_change: Location change data

        Returns:
            Processed location change, or None if invalid
        """
        # Get location ID or name
        location_id = loc_change.get("location_id")
        is_new = loc_change.get("is_new", False)

        # Validate location ID for existing locations
        if not is_new and location_id:
            # Try to resolve by name if not an ID
            if location_id not in self.card_manager.cards_by_type.get("location", {}):
                location_id_lower = location_id.lower()
                if location_id_lower in self.entity_ids.get("location", {}):
                    location_id = self.entity_ids["location"][location_id_lower]
                else:
                    # Location not found, treat as new
                    is_new = True

        # Process changes
        changes = loc_change.get("changes", {})

        # Return processed location change
        return {
            "location_id": location_id,
            "is_new": is_new,
            "name": loc_change.get("name", location_id) if is_new else None,
            "changes": changes
        }

    def _process_item_change(self, item_change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an item change.

        Args:
            item_change: Item change data

        Returns:
            Processed item change, or None if invalid
        """
        # Get item ID or name
        item_id = item_change.get("item_id")
        is_new = item_change.get("is_new", False)

        # Validate item ID for existing items
        if not is_new and item_id:
            # Try to resolve by name if not an ID
            if item_id not in self.card_manager.cards_by_type.get("item", {}):
                item_id_lower = item_id.lower()
                if item_id_lower in self.entity_ids.get("item", {}):
                    item_id = self.entity_ids["item"][item_id_lower]
                else:
                    # Item not found, treat as new
                    is_new = True

        # Process changes
        changes = item_change.get("changes", {})

        # Return processed item change
        return {
            "item_id": item_id,
            "is_new": is_new,
            "name": item_change.get("name", item_id) if is_new else None,
            "changes": changes
        }

    def _process_relationship_change(self, rel_change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a relationship change.

        Args:
            rel_change: Relationship change data

        Returns:
            Processed relationship change, or None if invalid
        """
        # Get entity IDs or names
        entity1_id = rel_change.get("entity1_id")
        entity2_id = rel_change.get("entity2_id")

        # Try to resolve entity IDs by name if not IDs
        for entity_type in ["character", "location", "item"]:
            # Entity 1
            if (entity1_id and
                    entity1_id not in self.card_manager.cards and
                    entity1_id.lower() in self.entity_ids.get(entity_type, {})):
                entity1_id = self.entity_ids[entity_type][entity1_id.lower()]

            # Entity 2
            if (entity2_id and
                    entity2_id not in self.card_manager.cards and
                    entity2_id.lower() in self.entity_ids.get(entity_type, {})):
                entity2_id = self.entity_ids[entity_type][entity2_id.lower()]

        # Validate entity IDs
        if not entity1_id or not entity2_id:
            return None

        # Return processed relationship change
        return {
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
            "relationship_type": rel_change.get("relationship_type", "unspecified"),
            "strength": rel_change.get("strength", 5),
            "emotions": rel_change.get("emotions", {})
        }

    def _process_story_change(self, story_change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a story change.

        Args:
            story_change: Story change data

        Returns:
            Processed story change, or None if invalid
        """
        # Get story ID or name
        story_id = story_change.get("story_id")
        is_new = story_change.get("is_new", False)

        # Validate story ID for existing stories
        if not is_new and story_id:
            # Try to find story by ID or name
            found = False
            for existing_id, story in self.card_manager.cards_by_type.get("story", {}).items():
                if existing_id == story_id or story.name.lower() == story_id.lower():
                    story_id = existing_id
                    found = True
                    break

            if not found:
                # Story not found, treat as new
                is_new = True

        # Process changes
        changes = story_change.get("changes", {})

        # Process entity references in changes
        if "involved_characters" in changes:
            changes["involved_characters"] = [
                self._resolve_entity_id(char_id, "character")
                for char_id in changes["involved_characters"]
            ]

        if "involved_locations" in changes:
            changes["involved_locations"] = [
                self._resolve_entity_id(loc_id, "location")
                for loc_id in changes["involved_locations"]
            ]

        # Return processed story change
        return {
            "story_id": story_id,
            "is_new": is_new,
            "name": story_change.get("name", story_id) if is_new else None,
            "changes": changes
        }

    def _process_current_focus(self, focus_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process current focus data.

        Args:
            focus_data: Current focus data

        Returns:
            Processed current focus
        """
        processed_focus = {
            "characters": [],
            "location": None,
            "items": []
        }

        # Process character IDs
        for char_id in focus_data.get("characters", []):
            resolved_id = self._resolve_entity_id(char_id, "character")
            if resolved_id:
                processed_focus["characters"].append(resolved_id)

        # Process location ID
        location_id = focus_data.get("location")
        if location_id:
            processed_focus["location"] = self._resolve_entity_id(location_id, "location")

        # Process item IDs
        for item_id in focus_data.get("items", []):
            resolved_id = self._resolve_entity_id(item_id, "item")
            if resolved_id:
                processed_focus["items"].append(resolved_id)

        return processed_focus

    def _resolve_entity_id(self, entity_id: str, entity_type: str) -> Optional[str]:
        """
        Resolve an entity ID or name to an entity ID.

        Args:
            entity_id: Entity ID or name
            entity_type: Type of entity

        Returns:
            Resolved entity ID, or None if not found
        """
        if not entity_id:
            return None

        # Check if it's a valid entity ID
        if entity_id in self.card_manager.cards_by_type.get(entity_type, {}):
            return entity_id

        # Try to resolve by name
        entity_id_lower = entity_id.lower()
        if entity_id_lower in self.entity_ids.get(entity_type, {}):
            return self.entity_ids[entity_type][entity_id_lower]

        # Not found
        return entity_id  # Return as is for new entities

    def analyze_for_contradictions(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze extracted data for potential contradictions with existing data.

        Args:
            extracted_data: Processed extracted data

        Returns:
            List of potential contradictions
        """
        contradictions = []

        # Check character changes for contradictions
        for char_change in extracted_data.get("character_changes", []):
            if not char_change.get("is_new"):
                character_id = char_change.get("character_id")
                character = self.card_manager.get_card(character_id)

                if character:
                    # Check for contradictions in character attributes
                    char_contradictions = self._check_character_contradictions(character,
                                                                               char_change.get("changes", {}))
                    contradictions.extend(char_contradictions)

        # Check location changes for contradictions
        for loc_change in extracted_data.get("location_changes", []):
            if not loc_change.get("is_new"):
                location_id = loc_change.get("location_id")
                location = self.card_manager.get_card(location_id)

                if location:
                    # Check for contradictions in location attributes
                    loc_contradictions = self._check_location_contradictions(location, loc_change.get("changes", {}))
                    contradictions.extend(loc_contradictions)

        # Check item changes for contradictions
        for item_change in extracted_data.get("item_changes", []):
            if not item_change.get("is_new"):
                item_id = item_change.get("item_id")
                item = self.card_manager.get_card(item_id)

                if item:
                    # Check for contradictions in item attributes
                    item_contradictions = self._check_item_contradictions(item, item_change.get("changes", {}))
                    contradictions.extend(item_contradictions)

        return contradictions

    def _check_character_contradictions(self, character: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in character attributes.

        Args:
            character: Character card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check for location contradiction
        if "location" in changes and character.location != changes["location"]:
            # Check if this is a valid transition or a contradiction
            # For simplicity, we'll just flag it for review
            contradictions.append({
                "entity_id": character.id,
                "entity_type": "character",
                "attribute": "location",
                "existing_value": character.location,
                "proposed_value": changes["location"],
                "severity": "low"  # Characters can move, so this is a low severity contradiction
            })

        # Check for status contradiction
        if "status" in changes and character.status != changes["status"]:
            # Some status changes might be contradictions (e.g., dead -> alive)
            if (character.status == "dead" and changes["status"] != "resurrected"):
                contradictions.append({
                    "entity_id": character.id,
                    "entity_type": "character",
                    "attribute": "status",
                    "existing_value": character.status,
                    "proposed_value": changes["status"],
                    "severity": "high"  # Dead characters shouldn't become alive without resurrection
                })

        # Check for inventory contradictions
        if "inventory_removed" in changes:
            for item in changes["inventory_removed"]:
                if item not in character.inventory:
                    contradictions.append({
                        "entity_id": character.id,
                        "entity_type": "character",
                        "attribute": "inventory",
                        "existing_value": f"Does not have {item}",
                        "proposed_value": f"Removing {item}",
                        "severity": "medium"
                    })

        return contradictions

    def _check_location_contradictions(self, location: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in location attributes.

        Args:
            location: Location card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check for region contradiction
        if "region" in changes and location.region != changes["region"]:
            contradictions.append({
                "entity_id": location.id,
                "entity_type": "location",
                "attribute": "region",
                "existing_value": location.region,
                "proposed_value": changes["region"],
                "severity": "high"  # Regions shouldn't change arbitrarily
            })

        return contradictions

    def _check_item_contradictions(self, item: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in item attributes.

        Args:
            item: Item card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check for ownership contradiction
        if "owner" in changes and item.owner != changes["owner"]:
            # This might be a valid transfer or a contradiction
            # For simplicity, we'll just flag it for review if the previous owner still exists
            if item.owner and self.card_manager.get_card(item.owner):
                contradictions.append({
                    "entity_id": item.id,
                    "entity_type": "item",
                    "attribute": "owner",
                    "existing_value": item.owner,
                    "proposed_value": changes["owner"],
                    "severity": "low"  # Ownership can change, so this is a low severity contradiction
                })

        # Check for location contradiction
        if "location" in changes and item.location != changes["location"]:
            # Check if this is a valid transition or a contradiction
            contradictions.append({
                "entity_id": item.id,
                "entity_type": "item",
                "attribute": "location",
                "existing_value": item.location,
                "proposed_value": changes["location"],
                "severity": "low"  # Items can move, so this is a low severity contradiction
            })

        return contradictions

    def summarize_changes(self, extracted_data: Dict[str, Any]) -> str:
        """
        Generate a summary of the extracted changes.

        Args:
            extracted_data: Processed extracted data

        Returns:
            Summary string
        """
        summary = []

        # Summarize character changes
        for char_change in extracted_data.get("character_changes", []):
            character_id = char_change.get("character_id")
            is_new = char_change.get("is_new", False)
            name = char_change.get("name", character_id) if is_new else self.entity_names.get("character", {}).get(
                character_id, character_id)

            if is_new:
                summary.append(f"New character: {name}")
            else:
                changes = char_change.get("changes", {})

                if changes:
                    summary.append(f"Character '{name}' changes:")

                    if "location" in changes:
                        location_name = changes["location"]
                        location_id = self._resolve_entity_id(location_name, "location")
                        if location_id in self.entity_names.get("location", {}):
                            location_name = self.entity_names["location"][location_id]
                        summary.append(f"  - Moved to {location_name}")

                    if "status" in changes:
                        summary.append(f"  - Status changed to {changes['status']}")

                    if "inventory" in changes:
                        for item in changes["inventory"]:
                            summary.append(f"  - Gained {item}")

                    if "inventory_removed" in changes:
                        for item in changes["inventory_removed"]:
                            summary.append(f"  - Lost {item}")

                    if "traits" in changes:
                        for trait, value in changes["traits"].items():
                            summary.append(f"  - {trait.capitalize()}: {value}")

                    if "relationships" in changes:
                        for target_id, rel_info in changes["relationships"].items():
                            target_name = target_id
                            for entity_type in ["character", "location", "item"]:
                                if target_id in self.entity_names.get(entity_type, {}):
                                    target_name = self.entity_names[entity_type][target_id]
                                    break

                            rel_type = rel_info.get("type", "unknown")
                            strength = rel_info.get("strength", "unknown")
                            summary.append(f"  - Relationship with {target_name}: {rel_type} (strength: {strength})")

        # Summarize location changes
        for loc_change in extracted_data.get("location_changes", []):
            location_id = loc_change.get("location_id")
            is_new = loc_change.get("is_new", False)
            name = loc_change.get("name", location_id) if is_new else self.entity_names.get("location", {}).get(
                location_id, location_id)

            if is_new:
                summary.append(f"New location: {name}")
            else:
                changes = loc_change.get("changes", {})

                if changes:
                    summary.append(f"Location '{name}' changes:")

                    if "atmosphere" in changes:
                        summary.append(f"  - Atmosphere changed to {changes['atmosphere']}")

                    if "features" in changes:
                        for feature in changes["features"]:
                            summary.append(f"  - Added feature: {feature}")

                    if "inhabitants" in changes:
                        for inhabitant in changes["inhabitants"]:
                            inhabitant_name = inhabitant
                            if inhabitant in self.entity_names.get("character", {}):
                                inhabitant_name = self.entity_names["character"][inhabitant]
                            summary.append(f"  - New inhabitant: {inhabitant_name}")

        # Summarize item changes
        for item_change in extracted_data.get("item_changes", []):
            item_id = item_change.get("item_id")
            is_new = item_change.get("is_new", False)
            name = item_change.get("name", item_id) if is_new else self.entity_names.get("item", {}).get(item_id,
                                                                                                         item_id)

            if is_new:
                summary.append(f"New item: {name}")
            else:
                changes = item_change.get("changes", {})

                if changes:
                    summary.append(f"Item '{name}' changes:")

                    if "owner" in changes:
                        owner_name = changes["owner"]
                        owner_id = self._resolve_entity_id(owner_name, "character")
                        if owner_id in self.entity_names.get("character", {}):
                            owner_name = self.entity_names["character"][owner_id]
                        summary.append(f"  - New owner: {owner_name}")

                    if "location" in changes:
                        location_name = changes["location"]
                        location_id = self._resolve_entity_id(location_name, "location")
                        if location_id in self.entity_names.get("location", {}):
                            location_name = self.entity_names["location"][location_id]
                        summary.append(f"  - Moved to {location_name}")

                    if "properties" in changes:
                        for prop, value in changes["properties"].items():
                            summary.append(f"  - {prop.capitalize()}: {value}")

        # Summarize relationship changes
        for rel_change in extracted_data.get("relationship_changes", []):
            entity1_id = rel_change.get("entity1_id")
            entity2_id = rel_change.get("entity2_id")

            entity1_name = entity1_id
            entity2_name = entity2_id

            # Get entity names
            for entity_type in ["character", "location", "item"]:
                if entity1_id in self.entity_names.get(entity_type, {}):
                    entity1_name = self.entity_names[entity_type][entity1_id]

                if entity2_id in self.entity_names.get(entity_type, {}):
                    entity2_name = self.entity_names[entity_type][entity2_id]

            rel_type = rel_change.get("relationship_type", "unspecified")
            strength = rel_change.get("strength", 5)

            summary.append(f"Relationship between {entity1_name} and {entity2_name}: {rel_type} (strength: {strength})")

            if "emotions" in rel_change:
                for emotion, value in rel_change["emotions"].items():
                    summary.append(f"  - {emotion.capitalize()}: {value}")

        # Summarize story developments
        for story_change in extracted_data.get("story_developments", []):
            story_id = story_change.get("story_id")
            is_new = story_change.get("is_new", False)
            name = story_change.get("name", story_id) if is_new else None

            if name is None:
                # Try to find story name
                for story in self.card_manager.cards_by_type.get("story", {}).values():
                    if story.id == story_id or story.name == story_id:
                        name = story.name
                        break

                if name is None:
                    name = story_id

            if is_new:
                summary.append(f"New story: {name}")
            else:
                changes = story_change.get("changes", {})

                if changes:
                    summary.append(f"Story '{name}' developments:")

                    if "status" in changes:
                        summary.append(f"  - Status changed to {changes['status']}")

                    if "involved_characters" in changes:
                        for char_id in changes["involved_characters"]:
                            char_name = char_id
                            if char_id in self.entity_names.get("character", {}):
                                char_name = self.entity_names["character"][char_id]
                            summary.append(f"  - Character involved: {char_name}")

                    if "involved_locations" in changes:
                        for loc_id in changes["involved_locations"]:
                            loc_name = loc_id
                            if loc_id in self.entity_names.get("location", {}):
                                loc_name = self.entity_names["location"][loc_id]
                            summary.append(f"  - Location involved: {loc_name}")

                    if "description" in changes:
                        summary.append(f"  - Development: {changes['description']}")

        return "\n".join(summary)