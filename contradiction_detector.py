"""
System for detecting and resolving contradictions in the game state.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set

from llm_interface import LLMInterface
from card_manager import CardManager
from config import CONTRADICTION_THRESHOLD

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContradictionDetector:
    """
    Detects and resolves contradictions in the game state.
    """

    def __init__(self, llm_interface: LLMInterface, card_manager: CardManager):
        """
        Initialize the contradiction detector.

        Args:
            llm_interface: Interface to the language model
            card_manager: Card manager instance
        """
        self.llm = llm_interface
        self.card_manager = card_manager
        self.contradiction_history = []

    def check_contradictions(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in the extracted data against the current state.

        Args:
            extracted_data: Extracted data to check

        Returns:
            List of detected contradictions
        """
        contradictions = []

        # Check character contradictions
        for char_change in extracted_data.get("character_changes", []):
            if not char_change.get("is_new", False):
                char_id = char_change.get("character_id")
                character = self.card_manager.get_card(char_id)

                if character:
                    char_contradictions = self._check_character_contradictions(
                        character,
                        char_change.get("changes", {})
                    )
                    contradictions.extend(char_contradictions)

        # Check location contradictions
        for loc_change in extracted_data.get("location_changes", []):
            if not loc_change.get("is_new", False):
                loc_id = loc_change.get("location_id")
                location = self.card_manager.get_card(loc_id)

                if location:
                    loc_contradictions = self._check_location_contradictions(
                        location,
                        loc_change.get("changes", {})
                    )
                    contradictions.extend(loc_contradictions)

        # Check item contradictions
        for item_change in extracted_data.get("item_changes", []):
            if not item_change.get("is_new", False):
                item_id = item_change.get("item_id")
                item = self.card_manager.get_card(item_id)

                if item:
                    item_contradictions = self._check_item_contradictions(
                        item,
                        item_change.get("changes", {})
                    )
                    contradictions.extend(item_contradictions)

        # Check relationship contradictions
        for rel_change in extracted_data.get("relationship_changes", []):
            rel_contradictions = self._check_relationship_contradictions(rel_change)
            contradictions.extend(rel_contradictions)

        # Check story contradictions
        for story_change in extracted_data.get("story_developments", []):
            if not story_change.get("is_new", False):
                story_id = story_change.get("story_id")
                story = self.card_manager.get_card(story_id)

                if story:
                    story_contradictions = self._check_story_contradictions(
                        story,
                        story_change.get("changes", {})
                    )
                    contradictions.extend(story_contradictions)

        # Record contradictions in history
        for contradiction in contradictions:
            self._record_contradiction(contradiction)

        return contradictions

    def _check_character_contradictions(self, character: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in character changes.

        Args:
            character: Character card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check location contradiction
        if "location" in changes:
            new_location = changes["location"]
            if hasattr(character, "location") and character.location != new_location:
                # This might be a valid movement or a contradiction
                contradiction = {
                    "type": "character_location",
                    "entity_id": character.id,
                    "entity_name": character.name,
                    "attribute": "location",
                    "current_value": character.location,
                    "new_value": new_location,
                    "severity": "low"  # Low severity because movement is common
                }

                contradictions.append(contradiction)

        # Check status contradiction
        if "status" in changes:
            new_status = changes["status"]
            if hasattr(character, "status") and character.status != new_status:
                severity = "low"

                # Higher severity for specific status changes
                if character.status == "dead" and new_status not in ["undead", "resurrected", "ghost"]:
                    severity = "high"

                contradiction = {
                    "type": "character_status",
                    "entity_id": character.id,
                    "entity_name": character.name,
                    "attribute": "status",
                    "current_value": character.status,
                    "new_value": new_status,
                    "severity": severity
                }

                contradictions.append(contradiction)

        # Check inventory contradictions
        if "inventory_removed" in changes and hasattr(character, "inventory"):
            for item in changes["inventory_removed"]:
                if item not in character.inventory:
                    contradiction = {
                        "type": "character_inventory",
                        "entity_id": character.id,
                        "entity_name": character.name,
                        "attribute": "inventory_removed",
                        "current_value": "Item not in inventory",
                        "new_value": f"Removing {item}",
                        "severity": "medium"
                    }

                    contradictions.append(contradiction)

        return contradictions

    def _check_location_contradictions(self, location: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in location changes.

        Args:
            location: Location card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check region contradiction (regions shouldn't change normally)
        if "region" in changes:
            new_region = changes["region"]
            if hasattr(location, "region") and location.region and location.region != new_region:
                contradiction = {
                    "type": "location_region",
                    "entity_id": location.id,
                    "entity_name": location.name,
                    "attribute": "region",
                    "current_value": location.region,
                    "new_value": new_region,
                    "severity": "high"  # High severity because regions shouldn't change often
                }

                contradictions.append(contradiction)

        # Check features contradictions - features that were removed
        if "features" in changes and hasattr(location, "features"):
            new_features_set = set(changes["features"])
            current_features_set = set(location.features)

            # Check for features that were in the location but are not in the new set
            removed_features = current_features_set - new_features_set

            if removed_features:
                contradiction = {
                    "type": "location_features",
                    "entity_id": location.id,
                    "entity_name": location.name,
                    "attribute": "features",
                    "current_value": f"Has features: {', '.join(removed_features)}",
                    "new_value": "Features not present in update",
                    "severity": "medium"  # Medium severity because features might be destroyed but shouldn't disappear
                }

                contradictions.append(contradiction)

        # More location-specific checks could be added here

        return contradictions

    def _check_item_contradictions(self, item: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in item changes.

        Args:
            item: Item card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check owner contradiction - simultaneous ownership
        if "owner" in changes and "location" in changes:
            new_owner = changes["owner"]
            new_location = changes["location"]

            # If both owner and location are specified and not consistent with each other
            if new_owner and new_location and new_owner != new_location:
                # This might be a valid case (item in a location while owned) or a contradiction
                character = self.card_manager.get_card(new_owner)

                if character and hasattr(character, "location") and character.location != new_location:
                    contradiction = {
                        "type": "item_location_owner",
                        "entity_id": item.id,
                        "entity_name": item.name,
                        "attribute": "owner_location",
                        "current_value": f"Owner: {item.owner}, Location: {item.location}",
                        "new_value": f"Owner: {new_owner}, Location: {new_location}",
                        "severity": "medium"  # Medium severity because this is often a real contradiction
                    }

                    contradictions.append(contradiction)

        # Check property contradictions - properties that shouldn't change
        if "properties" in changes and hasattr(item, "properties"):
            for prop, new_value in changes["properties"].items():
                if prop in item.properties and item.properties[prop] != new_value:
                    # Some properties are immutable (e.g., material, size)
                    immutable_properties = ["material", "size", "weight", "composition"]

                    if prop in immutable_properties:
                        contradiction = {
                            "type": "item_property",
                            "entity_id": item.id,
                            "entity_name": item.name,
                            "attribute": f"property_{prop}",
                            "current_value": item.properties[prop],
                            "new_value": new_value,
                            "severity": "high"  # High severity for immutable properties
                        }

                        contradictions.append(contradiction)

        return contradictions

    def _check_relationship_contradictions(self, rel_change: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in relationship changes.

        Args:
            rel_change: Relationship change data

        Returns:
            List of contradictions
        """
        contradictions = []

        entity1_id = rel_change.get("entity1_id")
        entity2_id = rel_change.get("entity2_id")
        relationship_type = rel_change.get("relationship_type")
        strength = rel_change.get("strength", 5)

        # Check if entities exist
        entity1 = self.card_manager.get_card(entity1_id)
        entity2 = self.card_manager.get_card(entity2_id)

        if not entity1 or not entity2:
            # Not a contradiction, just a potential error
            return contradictions

        # Check for existing relationships between these entities
        relationships = []
        for card in self.card_manager.cards_by_type.get("relationship", {}).values():
            if (card.entity1 == entity1_id and card.entity2 == entity2_id) or \
                    (card.entity1 == entity2_id and card.entity2 == entity1_id):
                relationships.append(card)

        if relationships:
            for relationship in relationships:
                # Check for relationship type contradictions
                if hasattr(relationship, "relationship_type") and relationship.relationship_type != relationship_type:
                    # This might be a valid change or a contradiction

                    # Check for incompatible relationship types
                    incompatible_pairs = [
                        ({"romantic", "family", "parent", "child", "sibling"}, {"enemy", "nemesis", "rival"}),
                        ({"ally", "friend", "protector"}, {"enemy", "nemesis", "rival"})
                    ]

                    for group1, group2 in incompatible_pairs:
                        if (relationship.relationship_type in group1 and relationship_type in group2) or \
                                (relationship.relationship_type in group2 and relationship_type in group1):
                            contradiction = {
                                "type": "relationship_type",
                                "entity_id": relationship.id,
                                "entity_name": relationship.name,
                                "attribute": "relationship_type",
                                "current_value": relationship.relationship_type,
                                "new_value": relationship_type,
                                "severity": "medium"  # Medium severity because relationships can change
                            }

                            contradictions.append(contradiction)

                # Check for relationship strength contradictions
                if hasattr(relationship, "strength") and abs(relationship.strength - strength) > 5:
                    # Large changes in relationship strength might be contradictions
                    contradiction = {
                        "type": "relationship_strength",
                        "entity_id": relationship.id,
                        "entity_name": relationship.name,
                        "attribute": "strength",
                        "current_value": relationship.strength,
                        "new_value": strength,
                        "severity": "low"  # Low severity because strength can change
                    }

                    contradictions.append(contradiction)

        return contradictions

    def _check_story_contradictions(self, story: Any, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictions in story changes.

        Args:
            story: Story card
            changes: Proposed changes

        Returns:
            List of contradictions
        """
        contradictions = []

        # Check status contradiction
        if "status" in changes:
            new_status = changes["status"]
            if hasattr(story, "status") and story.status != new_status:
                # Check for invalid status transitions
                if story.status == "completed" and new_status not in ["archived", "epilogue"]:
                    contradiction = {
                        "type": "story_status",
                        "entity_id": story.id,
                        "entity_name": story.name,
                        "attribute": "status",
                        "current_value": story.status,
                        "new_value": new_status,
                        "severity": "high"  # High severity because completed stories shouldn't become active again
                    }

                    contradictions.append(contradiction)

                if story.status == "failed" and new_status == "active":
                    contradiction = {
                        "type": "story_status",
                        "entity_id": story.id,
                        "entity_name": story.name,
                        "attribute": "status",
                        "current_value": story.status,
                        "new_value": new_status,
                        "severity": "high"  # High severity because failed stories shouldn't become active again
                    }

                    contradictions.append(contradiction)

        return contradictions

    def _record_contradiction(self, contradiction: Dict[str, Any]) -> None:
        """
        Record a contradiction in the history.

        Args:
            contradiction: Contradiction data
        """
        contradiction_record = contradiction.copy()
        contradiction_record["timestamp"] = time.time()
        contradiction_record["resolved"] = False

        self.contradiction_history.append(contradiction_record)

    def resolve_contradictions(self, contradictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve detected contradictions.

        Args:
            contradictions: List of contradictions to resolve

        Returns:
            Dictionary of resolved contradictions
        """
        resolutions = {}

        for contradiction in contradictions:
            resolution = self._resolve_contradiction(contradiction)

            if resolution:
                contradiction_id = f"{contradiction['type']}_{contradiction['entity_id']}_{contradiction['attribute']}"
                resolutions[contradiction_id] = resolution

                # Mark as resolved in history
                for record in self.contradiction_history:
                    if (record["type"] == contradiction["type"] and
                            record["entity_id"] == contradiction["entity_id"] and
                            record["attribute"] == contradiction["attribute"] and
                            not record["resolved"]):
                        record["resolved"] = True
                        record["resolution"] = resolution
                        break

        return resolutions

    def _resolve_contradiction(self, contradiction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Resolve a single contradiction.

        Args:
            contradiction: Contradiction to resolve

        Returns:
            Resolution data, or None if unresolved
        """
        # Default to accepting newer information for low severity contradictions
        if contradiction["severity"] == "low":
            return {
                "action": "accept_new",
                "reason": "Low severity contradiction - newer information accepted",
                "value": contradiction["new_value"]
            }

        # For medium and high severity contradictions, use LLM to help resolve
        resolution = self._get_resolution_from_llm(contradiction)

        if resolution:
            return resolution

        # Fallback: create a manual resolution request
        return {
            "action": "manual_review",
            "reason": f"{contradiction['severity'].capitalize()} severity contradiction requires review",
            "current_value": contradiction["current_value"],
            "new_value": contradiction["new_value"]
        }

    def _get_resolution_from_llm(self, contradiction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Use the LLM to help resolve a contradiction.

        Args:
            contradiction: Contradiction to resolve

        Returns:
            Resolution data, or None if the LLM couldn't resolve it
        """
        # Get entity information
        entity = self.card_manager.get_card(contradiction["entity_id"])
        entity_info = self.card_manager.get_card_summary(contradiction["entity_id"]) if entity else "Unknown entity"

        # Get recent history for the entity
        entity_history = []
        if entity and hasattr(entity, "history") and entity.history:
            for history_entry in entity.history[-5:]:  # Get last 5 history entries
                entity_history.append(
                    f"- {history_entry.get('timestamp', 'Unknown time')}: {str(history_entry.get('changes', {}))}")

        entity_history_text = "\n".join(entity_history) if entity_history else "No history available"

        # Create prompt for the LLM
        prompt = f"""
        Help resolve a contradiction in an RPG game state:

        ENTITY INFORMATION:
        {entity_info}

        RECENT ENTITY HISTORY:
        {entity_history_text}

        CONTRADICTION:
        Type: {contradiction['type']}
        Attribute: {contradiction['attribute']}
        Current value: {contradiction['current_value']}
        New value: {contradiction['new_value']}
        Severity: {contradiction['severity']}

        Please analyze this contradiction and suggest how to resolve it.
        Options include:
        1. Accept the new value (if it's a valid change/development)
        2. Keep the current value (if the new information appears mistaken)
        3. Merge the values (if both contain partial truth)
        4. Create a narrative explanation (if there's a way to explain the contradiction in-story)

        RESPOND WITH JSON in this format:
        {{
            "action": "accept_new" or "keep_current" or "merge" or "narrative",
            "reason": "Brief explanation of your decision",
            "value": "The value to use (either current, new, or merged value)",
            "narrative": "Optional narrative explanation if needed"
        }}
        """

        try:
            resolution_data = self.llm.extract_structured_data(prompt)

            if "action" in resolution_data and "reason" in resolution_data:
                return resolution_data
        except Exception as e:
            logger.error(f"Error getting resolution from LLM: {e}")

        return None

    def generate_narrative_explanation(self, contradiction: Dict[str, Any], resolution: Dict[str, Any]) -> str:
        """
        Generate a narrative explanation for a contradiction.

        Args:
            contradiction: Contradiction data
            resolution: Resolution data

        Returns:
            Narrative explanation
        """
        if "narrative" in resolution and resolution["narrative"]:
            return resolution["narrative"]

        # If no narrative in resolution, generate one
        entity = self.card_manager.get_card(contradiction["entity_id"])
        entity_name = entity.name if entity else contradiction["entity_name"]

        prompt = f"""
        Create a brief narrative explanation for this change in an RPG game:

        ENTITY: {entity_name}
        ATTRIBUTE: {contradiction['attribute']}
        CHANGE: From '{contradiction['current_value']}' to '{contradiction['new_value']}'
        RESOLUTION: {resolution['action']} - {resolution['reason']}

        Write a 1-3 sentence narrative explanation that a game master could use to explain this change.
        Focus on making it feel natural within a fantasy RPG world.
        """

        try:
            response = self.llm.generate_response(prompt, "")
            return response
        except Exception as e:
            logger.error(f"Error generating narrative explanation: {e}")
            return f"The change from {contradiction['current_value']} to {resolution['value']} occurs."

    def run_consistency_check(self) -> List[Dict[str, Any]]:
        """
        Run a comprehensive consistency check across the entire game state.

        Returns:
            List of inconsistencies found
        """
        inconsistencies = []

        # Check character-location consistency
        inconsistencies.extend(self._check_character_location_consistency())

        # Check item-owner consistency
        inconsistencies.extend(self._check_item_owner_consistency())

        # Check relationship consistency
        inconsistencies.extend(self._check_relationship_consistency())

        # Check story-status consistency
        inconsistencies.extend(self._check_story_status_consistency())

        return inconsistencies

    def _check_character_location_consistency(self) -> List[Dict[str, Any]]:
        """
        Check for inconsistencies in character locations.

        Returns:
            List of inconsistencies
        """
        inconsistencies = []

        for character in self.card_manager.cards_by_type.get("character", {}).values():
            if hasattr(character, "location") and character.location:
                location = self.card_manager.get_card(character.location)

                if not location:
                    # Character is in a location that doesn't exist
                    inconsistency = {
                        "type": "character_location",
                        "entity_id": character.id,
                        "entity_name": character.name,
                        "description": f"Character is in non-existent location: {character.location}",
                        "severity": "medium"
                    }

                    inconsistencies.append(inconsistency)

        return inconsistencies

    def _check_item_owner_consistency(self) -> List[Dict[str, Any]]:
        """
        Check for inconsistencies in item ownership.

        Returns:
            List of inconsistencies
        """
        inconsistencies = []

        for item in self.card_manager.cards_by_type.get("item", {}).values():
            if hasattr(item, "owner") and item.owner:
                owner = self.card_manager.get_card(item.owner)

                if not owner:
                    # Item is owned by an entity that doesn't exist
                    inconsistency = {
                        "type": "item_owner",
                        "entity_id": item.id,
                        "entity_name": item.name,
                        "description": f"Item is owned by non-existent entity: {item.owner}",
                        "severity": "medium"
                    }

                    inconsistencies.append(inconsistency)
                elif hasattr(owner, "inventory") and item.id not in owner.inventory:
                    # Item is owned by a character but not in their inventory
                    inconsistency = {
                        "type": "item_inventory",
                        "entity_id": item.id,
                        "entity_name": item.name,
                        "description": f"Item is owned by {owner.name} but not in their inventory",
                        "severity": "low"
                    }

                    inconsistencies.append(inconsistency)

            if hasattr(item, "location") and item.location:
                location = self.card_manager.get_card(item.location)

                if not location:
                    # Item is in a location that doesn't exist
                    inconsistency = {
                        "type": "item_location",
                        "entity_id": item.id,
                        "entity_name": item.name,
                        "description": f"Item is in non-existent location: {item.location}",
                        "severity": "medium"
                    }

                    inconsistencies.append(inconsistency)

        return inconsistencies

    def _check_relationship_consistency(self) -> List[Dict[str, Any]]:
        """
        Check for inconsistencies in relationships.

        Returns:
            List of inconsistencies
        """
        inconsistencies = []

        for relationship in self.card_manager.cards_by_type.get("relationship", {}).values():
            if hasattr(relationship, "entity1") and hasattr(relationship, "entity2"):
                entity1 = self.card_manager.get_card(relationship.entity1)
                entity2 = self.card_manager.get_card(relationship.entity2)

                if not entity1 or not entity2:
                    # Relationship between entities that don't exist
                    inconsistency = {
                        "type": "relationship_entities",
                        "entity_id": relationship.id,
                        "entity_name": relationship.name,
                        "description": f"Relationship references non-existent entities: {relationship.entity1} and/or {relationship.entity2}",
                        "severity": "high"
                    }

                    inconsistencies.append(inconsistency)

        return inconsistencies

    def _check_story_status_consistency(self) -> List[Dict[str, Any]]:
        """
        Check for inconsistencies in story statuses.

        Returns:
            List of inconsistencies
        """
        inconsistencies = []

        for story in self.card_manager.cards_by_type.get("story", {}).values():
            if hasattr(story, "prerequisites") and hasattr(story, "status"):
                if story.status == "active":
                    # Check if prerequisites are met
                    for prereq_id in story.prerequisites:
                        prereq = self.card_manager.get_card(prereq_id)

                        if prereq and hasattr(prereq, "status") and prereq.status not in ["completed", "succeeded"]:
                            # Story is active but prerequisites are not met
                            inconsistency = {
                                "type": "story_prerequisites",
                                "entity_id": story.id,
                                "entity_name": story.name,
                                "description": f"Story is active but prerequisite {prereq.name} is not completed",
                                "severity": "medium"
                            }

                            inconsistencies.append(inconsistency)

            # Check for invalid entities in story
            for attr in ["involved_characters", "involved_locations", "involved_items"]:
                if hasattr(story, attr):
                    for entity_id in getattr(story, attr):
                        entity = self.card_manager.get_card(entity_id)

                        if not entity:
                            # Story references non-existent entity
                            inconsistency = {
                                "type": "story_entity_reference",
                                "entity_id": story.id,
                                "entity_name": story.name,
                                "description": f"Story references non-existent entity in {attr}: {entity_id}",
                                "severity": "medium"
                            }

                            inconsistencies.append(inconsistency)

        return inconsistencies