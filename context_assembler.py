"""
Assembles relevant context for the AI based on the current game state.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Set

from card_manager import CardManager
from vector_store import VectorStore
from config import MAX_CONTEXT_TOKENS, MEMORY_RELEVANCE_THRESHOLD

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    Assembles relevant context for the AI based on the current game state.
    """

    def __init__(self, card_manager: CardManager, vector_store: VectorStore):
        """
        Initialize the context assembler.

        Args:
            card_manager: Card manager instance
            vector_store: Vector store instance
        """
        self.card_manager = card_manager
        self.vector_store = vector_store

    def assemble_context(self, current_situation: str,
                         recent_history: List[Dict[str, str]],
                         known_focus: Optional[Dict[str, Any]] = None) -> str:
        """
        Assemble a comprehensive context for the AI.

        Args:
            current_situation: Description of the current situation
            recent_history: Recent interaction history
            known_focus: Known entities in focus (characters, location, etc.)

        Returns:
            Assembled context
        """
        # Identify active entities if not provided
        if known_focus is None:
            active_entities = self._identify_active_entities(current_situation, recent_history)
        else:
            active_entities = known_focus

        # Fetch entity information
        character_contexts = self._get_character_contexts(active_entities.get("characters", []))
        location_context = self._get_location_context(active_entities.get("location"))
        item_contexts = self._get_item_contexts(active_entities.get("items", []))

        # Fetch relevant memories
        memory_contexts = self._get_relevant_memories(
            current_situation,
            active_entities.get("characters", []),
            active_entities.get("location")
        )

        # Fetch active stories
        story_contexts = self._get_story_contexts(active_entities)

        # Assemble the full context
        full_context = self._format_context(
            current_situation,
            recent_history,
            character_contexts,
            location_context,
            item_contexts,
            memory_contexts,
            story_contexts
        )

        return full_context

    def _identify_active_entities(self, current_situation: str, recent_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Identify active entities based on the current situation and recent history.

        Args:
            current_situation: Description of the current situation
            recent_history: Recent interaction history

        Returns:
            Dictionary of active entities
        """
        # Combine current situation and recent history for context
        full_text = current_situation
        for interaction in recent_history[-3:]:  # Use last 3 interactions
            full_text += f"\n{interaction.get('user', '')}\n{interaction.get('ai', '')}"

        # Search for similar memories to find relevant entities
        similar_memories = self.vector_store.search_similar(full_text, top_k=5)

        # Extract entities from similar memories
        active_characters = set()
        active_items = set()
        active_location = None

        for memory in similar_memories:
            # Extract characters
            if "entities" in memory:
                for entity in memory.get("entities", []):
                    if entity.get("type") == "character":
                        active_characters.add(entity.get("id"))
                    elif entity.get("type") == "item":
                        active_items.add(entity.get("id"))

            # Extract location
            if "location" in memory and not active_location:
                active_location = memory.get("location")

        # If no location found, try to find the most mentioned location
        if not active_location:
            location_counts = {}
            for memory in similar_memories:
                if "location" in memory:
                    location_id = memory.get("location")
                    location_counts[location_id] = location_counts.get(location_id, 0) + 1

            if location_counts:
                active_location = max(location_counts.items(), key=lambda x: x[1])[0]

        # Check if any characters are at the active location
        if active_location:
            for character in self.card_manager.cards_by_type.get("character", {}).values():
                if hasattr(character, "location") and character.location == active_location:
                    active_characters.add(character.id)

        return {
            "characters": list(active_characters),
            "location": active_location,
            "items": list(active_items)
        }

    def _get_character_contexts(self, character_ids: List[str]) -> List[str]:
        """
        Get context information for characters.

        Args:
            character_ids: List of character IDs

        Returns:
            List of character context strings
        """
        character_contexts = []

        for char_id in character_ids:
            character = self.card_manager.get_card(char_id)

            if character and character.type == "character":
                # Get character information
                char_context = self._format_character_context(character)
                character_contexts.append(char_context)

        return character_contexts

    def _format_character_context(self, character: Any) -> str:
        """
        Format a character's information for inclusion in context.

        Args:
            character: Character card

        Returns:
            Formatted character context
        """
        # Format traits
        traits_str = ""
        if hasattr(character, "traits"):
            traits_str = ", ".join(f"{k}: {v}" for k, v in character.traits.items())

        # Format inventory
        inventory_str = ""
        if hasattr(character, "inventory"):
            inventory_str = ", ".join(character.inventory) if character.inventory else "None"

        # Format relationships
        relationships_str = ""
        if hasattr(character, "relationships"):
            rel_items = []
            for target_id, rel_info in character.relationships.items():
                target = self.card_manager.get_card(target_id)
                target_name = target.name if target else target_id
                rel_type = rel_info.get("type", "unknown")
                rel_items.append(f"{target_name}: {rel_type}")

            relationships_str = ", ".join(rel_items) if rel_items else "None"

        # Get recent history (last 3 events)
        history_str = ""
        if hasattr(character, "history") and character.history:
            history_items = []
            for entry in character.history[-3:]:
                if "description" in entry.get("changes", {}):
                    history_items.append(entry["changes"]["description"])
                else:
                    # Summarize changes
                    changes = []
                    for k, v in entry.get("changes", {}).items():
                        changes.append(f"{k}: {v}")

                    if changes:
                        history_items.append(", ".join(changes))

            history_str = "\n  - " + "\n  - ".join(history_items) if history_items else "None"

        # Format the character context
        return f"""
CHARACTER: {character.name}
Description: {character.description}
Status: {getattr(character, 'status', 'Unknown')}
Traits: {traits_str}
Inventory: {inventory_str}
Relationships: {relationships_str}
Recent History: {history_str}
"""

    def _get_location_context(self, location_id: Optional[str]) -> str:
        """
        Get context information for a location.

        Args:
            location_id: Location ID

        Returns:
            Location context string
        """
        if not location_id:
            return "LOCATION: Unknown"

        location = self.card_manager.get_card(location_id)

        if not location or location.type != "location":
            return f"LOCATION: {location_id} (details unknown)"

        # Format features
        features_str = ""
        if hasattr(location, "features"):
            features_str = ", ".join(location.features) if location.features else "None"

        # Format inhabitants
        inhabitants_str = ""
        if hasattr(location, "inhabitants"):
            inhabitant_names = []
            for inhabitant_id in location.inhabitants:
                inhabitant = self.card_manager.get_card(inhabitant_id)
                inhabitant_names.append(inhabitant.name if inhabitant else inhabitant_id)

            inhabitants_str = ", ".join(inhabitant_names) if inhabitant_names else "None"

        # Format items
        items_str = ""
        if hasattr(location, "items"):
            item_names = []
            for item_id in location.items:
                item = self.card_manager.get_card(item_id)
                item_names.append(item.name if item else item_id)

            items_str = ", ".join(item_names) if item_names else "None"

        # Get characters currently at this location
        characters_at_location = []
        for character in self.card_manager.cards_by_type.get("character", {}).values():
            if hasattr(character, "location") and character.location == location_id:
                characters_at_location.append(character.name)

        characters_str = ", ".join(characters_at_location) if characters_at_location else "None"

        # Format the location context
        return f"""
LOCATION: {location.name}
Description: {location.description}
Region: {getattr(location, 'region', 'Unknown')}
Features: {features_str}
Atmosphere: {getattr(location, 'atmosphere', 'Unknown')}
Inhabitants: {inhabitants_str}
Items: {items_str}
Characters Present: {characters_str}
"""

    def _get_item_contexts(self, item_ids: List[str]) -> List[str]:
        """
        Get context information for items.

        Args:
            item_ids: List of item IDs

        Returns:
            List of item context strings
        """
        item_contexts = []

        for item_id in item_ids:
            item = self.card_manager.get_card(item_id)

            if item and item.type == "item":
                # Format properties
                properties_str = ""
                if hasattr(item, "properties"):
                    properties_str = ", ".join(f"{k}: {v}" for k, v in item.properties.items())

                # Format effects
                effects_str = ""
                if hasattr(item, "effects"):
                    effects_str = ", ".join(item.effects) if item.effects else "None"

                # Get owner name
                owner_name = "None"
                if hasattr(item, "owner") and item.owner:
                    owner = self.card_manager.get_card(item.owner)
                    owner_name = owner.name if owner else item.owner

                # Get location name
                location_name = "Unknown"
                if hasattr(item, "location") and item.location:
                    location = self.card_manager.get_card(item.location)
                    location_name = location.name if location else item.location

                # Format the item context
                item_context = f"""
ITEM: {item.name}
Description: {item.description}
Properties: {properties_str}
Effects: {effects_str}
Owner: {owner_name}
Location: {location_name}
"""
                item_contexts.append(item_context)

        return item_contexts

    def _get_relevant_memories(self, current_situation: str,
                               character_ids: List[str],
                               location_id: Optional[str]) -> List[str]:
        """
        Get relevant memories based on the current situation and active entities.

        Args:
            current_situation: Description of the current situation
            character_ids: List of active character IDs
            location_id: Active location ID

        Returns:
            List of relevant memory context strings
        """
        # Build filter conditions for the search
        filter_conditions = {}

        if character_ids:
            filter_conditions["entities"] = character_ids

        if location_id:
            filter_conditions["location"] = location_id

        # Search for relevant memories
        similar_memories = self.vector_store.search_similar(
            current_situation,
            top_k=10,
            filter_conditions=filter_conditions
        )

        # Filter memories by relevance
        relevant_memories = []
        for memory in similar_memories:
            if memory.get("score", 0) >= MEMORY_RELEVANCE_THRESHOLD:
                relevant_memories.append(memory)

        # Format the memories
        memory_contexts = []
        for memory in relevant_memories:
            # Format the memory context
            memory_text = memory.get("text", "")
            timestamp = memory.get("timestamp", 0)
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            importance = memory.get("importance", 0.5)

            # Add importance indicator for highly important memories
            importance_str = ""
            if importance > 0.8:
                importance_str = " [IMPORTANT]"
            elif importance > 0.6:
                importance_str = " [Significant]"

            memory_context = f"{time_str}{importance_str}: {memory_text}"
            memory_contexts.append(memory_context)

        return memory_contexts

    def _get_story_contexts(self, active_entities: Dict[str, Any]) -> List[str]:
        """
        Get context information for active stories relevant to the current situation.

        Args:
            active_entities: Dictionary of active entities

        Returns:
            List of story context strings
        """
        story_contexts = []

        # Get active stories
        active_stories = self.card_manager.get_active_stories()

        # Filter stories by relevance to active entities
        relevant_stories = []
        for story in active_stories:
            is_relevant = False

            # Check if story involves active characters
            if hasattr(story, "involved_characters"):
                for char_id in active_entities.get("characters", []):
                    if char_id in story.involved_characters:
                        is_relevant = True
                        break

            # Check if story involves active location
            if not is_relevant and hasattr(story, "involved_locations"):
                if active_entities.get("location") in story.involved_locations:
                    is_relevant = True

            # Check if story involves active items
            if not is_relevant and hasattr(story, "involved_items"):
                for item_id in active_entities.get("items", []):
                    if item_id in story.involved_items:
                        is_relevant = True
                        break

            if is_relevant:
                relevant_stories.append(story)

        # Format story contexts
        for story in relevant_stories:
            # Format involved characters
            char_names = []
            if hasattr(story, "involved_characters"):
                for char_id in story.involved_characters:
                    character = self.card_manager.get_card(char_id)
                    char_names.append(character.name if character else char_id)

            characters_str = ", ".join(char_names) if char_names else "None"

            # Format involved locations
            loc_names = []
            if hasattr(story, "involved_locations"):
                for loc_id in story.involved_locations:
                    location = self.card_manager.get_card(loc_id)
                    loc_names.append(location.name if location else loc_id)

            locations_str = ", ".join(loc_names) if loc_names else "None"

            # Format the story context
            story_context = f"""
STORY: {story.name}
Description: {story.description}
Status: {story.status}
Type: {getattr(story, 'plot_type', 'Unknown')}
Characters Involved: {characters_str}
Locations Involved: {locations_str}
"""
            story_contexts.append(story_context)

        return story_contexts

    def _format_context(self,
                        current_situation: str,
                        recent_history: List[Dict[str, str]],
                        character_contexts: List[str],
                        location_context: str,
                        item_contexts: List[str],
                        memory_contexts: List[str],
                        story_contexts: List[str]) -> str:
        """
        Format the complete context for the AI.

        Args:
            current_situation: Description of the current situation
            recent_history: Recent interaction history
            character_contexts: List of character context strings
            location_context: Location context string
            item_contexts: List of item context strings
            memory_contexts: List of memory context strings
            story_contexts: List of story context strings

        Returns:
            Formatted context
        """
        # Start with current location - always the most important
        context_parts = [
            "# CURRENT LOCATION",
            location_context
        ]

        # Add characters present - prioritize this for gameplay
        if character_contexts:
            context_parts.append("# CHARACTERS PRESENT")
            # Limit to 5 most important characters to reduce context size
            context_parts.extend(character_contexts[:5])

        # Add items - only if they exist and limit to 3 most important
        if item_contexts:
            context_parts.append("# NOTABLE ITEMS")
            context_parts.extend(item_contexts[:3])

        # Only include active storylines if we have any (often empty)
        # and limit to 2 most relevant to reduce context size
        if story_contexts:
            context_parts.append("# ACTIVE STORYLINES")
            context_parts.extend(story_contexts[:2])

        # Limit memory contexts to reduce context size
        if memory_contexts:
            context_parts.append("# RELEVANT MEMORIES")
            context_parts.extend(memory_contexts[:2])  # Only use top 2 memories

        # Add recent history - only the most recent 2 interactions
        if recent_history:
            context_parts.append("# RECENT INTERACTIONS")
            for interaction in recent_history[-2:]:  # Only the last 2 interactions
                context_parts.append(f"User: {interaction.get('user', '')}")
                context_parts.append(f"AI: {interaction.get('ai', '')}")

        # Add current situation - this is critical
        context_parts.append("# CURRENT SITUATION")
        context_parts.append(current_situation)

        # Add concise system instructions to encourage faster responses
        context_parts.append("""# INSTRUCTIONS
You are the Game Master for this RPG adventure. Maintain consistency with information above.
Respond quickly with concise, vivid descriptions (3-4 sentences) and direct responses to player actions.
Keep gameplay moving with fast-paced, interactive responses. If unsure, prioritize player agency.""")

        # Join all parts
        full_context = "\n\n".join(context_parts)

        return full_context