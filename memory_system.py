"""

Core memory system that integrates all components.

"""



import os

import json

import time

import logging

import uuid

from typing import Dict, List, Any, Optional, Set, Tuple



from PyQt5.QtGui import QTextCursor

from PyQt5.QtWidgets import QMessageBox, QDialog, QApplication, QInputDialog

from llm_interface import LLMInterface

from card_manager import CardManager

from vector_store import VectorStore

from information_extractor import InformationExtractor

from context_assembler import ContextAssembler

from contradiction_detector import ContradictionDetector

from config import CAMPAIGNS_DIR, LOGS_DIR, MAX_HISTORY_ITEMS, DEFAULT_CAMPAIGN_NAME



# Set up logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)





class MemorySystem:

    """

    Core memory system that integrates all components.

    """



    def __init__(self,

                 campaign_id: Optional[str] = None,

                 campaign_name: Optional[str] = None,

                 llm_interface: Optional[LLMInterface] = None):

        """

        Initialize the memory system.



        Args:

            campaign_id: Unique identifier for the campaign

            campaign_name: Name of the campaign

            llm_interface: Interface to the language model

        """

        # Set up campaign

        self.campaign_id = campaign_id if campaign_id else str(uuid.uuid4())

        self.campaign_name = campaign_name if campaign_name else DEFAULT_CAMPAIGN_NAME

        self.campaign_dir = os.path.join(CAMPAIGNS_DIR, self.campaign_id)

        self.logs_dir = os.path.join(self.campaign_dir, "logs")



        # Create directories

        os.makedirs(self.campaign_dir, exist_ok=True)

        os.makedirs(self.logs_dir, exist_ok=True)



        # Initialize LLM interface

        self.llm = llm_interface if llm_interface else LLMInterface()



        # Initialize components

        self.card_manager = CardManager(self.campaign_id)

        self.vector_store = VectorStore(self.campaign_id)

        self.information_extractor = InformationExtractor(self.llm, self.card_manager)

        self.context_assembler = ContextAssembler(self.card_manager, self.vector_store)

        self.contradiction_detector = ContradictionDetector(self.llm, self.card_manager)



        # Initialize session state

        self.session_history = []

        self.current_context = "Game is starting."

        self.current_focus = {

            "characters": [],

            "location": None,

            "items": []

        }



        # Performance optimization - cached data

        self._cached_context = None

        self._last_extraction_time = 0

        self._extraction_frequency = 3  # Only extract every X turns to reduce overhead

        self._last_metadata_save = 0



        # Load campaign metadata

        self._load_campaign_metadata()



    def _load_campaign_metadata(self) -> None:

        """

        Load campaign metadata from disk.

        """

        metadata_path = os.path.join(self.campaign_dir, "campaign_metadata.json")



        if os.path.exists(metadata_path):

            try:

                with open(metadata_path, "r") as f:

                    metadata = json.load(f)



                    self.campaign_name = metadata.get("name", self.campaign_name)

                    self.current_focus = metadata.get("current_focus", self.current_focus)



                    logger.info(f"Loaded campaign metadata: {self.campaign_name}")

                    logger.debug(f"Current focus from metadata: {self.current_focus}")

            except Exception as e:

                logger.error(f"Error loading campaign metadata: {e}")



    def _save_campaign_metadata(self) -> None:

        """Save campaign metadata and session history to disk."""

        # Only save metadata every 30 seconds to reduce disk I/O

        current_time = time.time()

        if hasattr(self, '_last_metadata_save') and current_time - self._last_metadata_save < 30:

            logger.debug("Skipping metadata save - last save was recent")

            return



        # Update last save time

        self._last_metadata_save = current_time



        metadata_path = os.path.join(self.campaign_dir, "campaign_metadata.json")

        session_path = os.path.join(self.campaign_dir, "session_history.json")



        # Try to read existing metadata first to preserve creation time

        created_time = current_time

        try:

            if os.path.exists(metadata_path):

                with open(metadata_path, "r") as f:

                    existing_metadata = json.load(f)

                    created_time = existing_metadata.get("created", created_time)

        except Exception:

            # If reading fails, just use current time as created time

            pass



        metadata = {

            "id": self.campaign_id,

            "name": self.campaign_name,

            "created": created_time,

            "last_modified": current_time,

            "current_focus": self.current_focus

        }



        try:

            # Save metadata with a temp file first to avoid corruption

            temp_path = metadata_path + ".temp"

            with open(temp_path, "w") as f:

                json.dump(metadata, f, indent=2)



            # Only replace if temp file was created successfully

            if os.path.exists(temp_path):

                # Create backup of existing file

                if os.path.exists(metadata_path):

                    backup_path = metadata_path + ".bak"

                    try:

                        os.replace(metadata_path, backup_path)

                    except Exception as backup_error:

                        logger.warning(f"Could not create backup of metadata: {backup_error}")



                # Replace with new file

                os.replace(temp_path, metadata_path)

                logger.debug(f"Saved campaign metadata: {self.campaign_name}")



            # Save session history separately - this can be large

            if self.session_history:

                temp_session_path = session_path + ".temp"

                with open(temp_session_path, "w") as f:

                    json.dump(self.session_history, f, indent=2)



                if os.path.exists(temp_session_path):

                    if os.path.exists(session_path):

                        session_backup_path = session_path + ".bak"

                        try:

                            os.replace(session_path, session_backup_path)

                        except Exception:

                            pass



                    os.replace(temp_session_path, session_path)

                    logger.debug(f"Saved session history with {len(self.session_history)} entries")

        except Exception as e:

            logger.error(f"Error saving campaign data: {e}")



    def _load_campaign_metadata(self) -> None:

        """

        Load campaign metadata and session history from disk.

        """

        metadata_path = os.path.join(self.campaign_dir, "campaign_metadata.json")

        session_path = os.path.join(self.campaign_dir, "session_history.json")



        # Load metadata

        if os.path.exists(metadata_path):

            try:

                with open(metadata_path, "r") as f:

                    metadata = json.load(f)



                    self.campaign_name = metadata.get("name", self.campaign_name)

                    self.current_focus = metadata.get("current_focus", self.current_focus)



                    logger.info(f"Loaded campaign metadata: {self.campaign_name}")

                    logger.debug(f"Current focus from metadata: {self.current_focus}")

            except Exception as e:

                logger.error(f"Error loading campaign metadata: {e}")



        # Load session history

        if os.path.exists(session_path):

            try:

                with open(session_path, "r") as f:

                    session_data = json.load(f)



                    if isinstance(session_data, list):

                        self.session_history = session_data

                        logger.info(f"Loaded session history with {len(self.session_history)} entries")

                    else:

                        logger.error("Session history data is not a valid list")

            except Exception as e:

                logger.error(f"Error loading session history: {e}")



    def process_turn(self, user_input: str) -> str:

        """

        Process a user's turn in the game.



        Args:

            user_input: User's text input



        Returns:

            AI's response

        """

        start_time = time.time()



        # First turn detection - use simplified context for extremely fast first response

        is_first_turn = len(self.session_history) == 0



        if is_first_turn:

            # For the first turn, use a minimal context to maximize response speed

            context = f"""# INSTRUCTIONS

You are the Game Master for this RPG adventure.

The game is just starting. Respond with a concise, engaging first response.

Keep your response under 3-4 sentences for a fast-paced experience.



PLAYER: {user_input}



GAME MASTER:"""

        else:

            # For subsequent turns, use a more streamlined context assembly

            # Avoid calling the full context assembler which can be slow

            active_chars = [self.card_manager.get_card(char_id).name

                          for char_id in self.current_focus.get("characters", [])

                          if self.card_manager.get_card(char_id)]



            loc_name = "unknown location"

            if self.current_focus.get("location"):

                loc_card = self.card_manager.get_card(self.current_focus.get("location"))

                if loc_card:

                    loc_name = loc_card.name



            # Ultra-lightweight context for speed

            context = f"""# CURRENT LOCATION

{loc_name}



# CHARACTERS PRESENT

{', '.join(active_chars) if active_chars else 'None'}



# RECENT INTERACTION

User: {self.session_history[-1].get('user', '') if self.session_history else ''}

AI: {self.session_history[-1].get('ai', '') if self.session_history else ''}



# CURRENT SITUATION

Player is in {loc_name} and just said: {user_input}



# INSTRUCTIONS

You are the Game Master. Respond quickly with a concise, direct response (3-4 sentences).

Focus on immediate reactions to the player's action. Keep gameplay fast-paced.

"""



        # Generate AI response with the lightweight context

        logger.info(f"Generating response for: '{user_input[:30]}...'")

        ai_response = self.llm.generate_response(user_input, context)



        # Immediately update basic state

        self.current_context = f"User: {user_input}\nAI: {ai_response}"



        # Add to session history

        self.session_history.append({

            "user": user_input,

            "ai": ai_response,

            "timestamp": time.time()

        })



        # Limit session history

        if len(self.session_history) > MAX_HISTORY_ITEMS:

            self.session_history = self.session_history[-MAX_HISTORY_ITEMS:]



        # Schedule background processing as a separate thread so it won't block next response

        import threading

        def background_processing():

            try:

                # First, do a proper context assembly for future turns

                full_context = self.context_assembler.assemble_context(

                    self.current_context,

                    self.session_history[-2:] if self.session_history else [],

                    self.current_focus

                )



                # Store this for future use

                self._cached_context = full_context



                # Extract information without blocking the response

                extracted_info = self.information_extractor.extract_information(

                    user_input, ai_response, self.current_context

                )



                # Only process further if we got meaningful information

                if extracted_info and len(extracted_info) > 1:

                    # Update game state with minimal checking

                    self._update_game_state(extracted_info)



                    # Update focus for next turn

                    if "current_focus" in extracted_info and extracted_info["current_focus"]:

                        self.current_focus = extracted_info["current_focus"]



                    # Minimal logging - just save the metadata occasionally

                    self._save_campaign_metadata()

            except Exception as e:

                logger.error(f"Background processing error: {e}")



        # Start background processing but don't wait for it

        if not is_first_turn:  # Skip expensive background processing on first turn

            thread = threading.Thread(target=background_processing)

            thread.daemon = True

            thread.start()



        # Log the response generation time

        response_time = time.time() - start_time

        logger.info(f"Response generation time: {response_time:.2f} seconds")



        return ai_response



    def _apply_resolutions(self, extracted_info: Dict[str, Any],

                           resolutions: Dict[str, Dict[str, Any]]) -> None:

        """

        Apply contradiction resolutions to the extracted information.



        Args:

            extracted_info: Extracted information

            resolutions: Resolutions for contradictions

        """

        # Process character changes

        for i, char_change in enumerate(extracted_info.get("character_changes", [])):

            char_id = char_change.get("character_id")

            changes = char_change.get("changes", {})



            # Check for character attribute resolutions

            for attr, value in list(changes.items()):

                contradiction_id = f"character_{char_id}_{attr}"



                if contradiction_id in resolutions:

                    resolution = resolutions[contradiction_id]



                    if resolution["action"] == "keep_current":

                        # Remove the attribute from changes

                        changes.pop(attr)

                    elif resolution["action"] == "merge":

                        # Update with merged value

                        changes[attr] = resolution["value"]

                    elif resolution["action"] == "accept_new":

                        # Keep the new value (no change needed)

                        pass



                    # Add narrative explanation if available

                    if "narrative" in resolution:

                        if "explanations" not in extracted_info:

                            extracted_info["explanations"] = []



                        extracted_info["explanations"].append({

                            "entity_id": char_id,

                            "attribute": attr,

                            "explanation": resolution["narrative"]

                        })



        # Process location changes

        for i, loc_change in enumerate(extracted_info.get("location_changes", [])):

            loc_id = loc_change.get("location_id")

            changes = loc_change.get("changes", {})



            # Check for location attribute resolutions

            for attr, value in list(changes.items()):

                contradiction_id = f"location_{loc_id}_{attr}"



                if contradiction_id in resolutions:

                    resolution = resolutions[contradiction_id]



                    if resolution["action"] == "keep_current":

                        # Remove the attribute from changes

                        changes.pop(attr)

                    elif resolution["action"] == "merge":

                        # Update with merged value

                        changes[attr] = resolution["value"]

                    elif resolution["action"] == "accept_new":

                        # Keep the new value (no change needed)

                        pass



                    # Add narrative explanation if available

                    if "narrative" in resolution:

                        if "explanations" not in extracted_info:

                            extracted_info["explanations"] = []



                        extracted_info["explanations"].append({

                            "entity_id": loc_id,

                            "attribute": attr,

                            "explanation": resolution["narrative"]

                        })



        # Process item changes

        for i, item_change in enumerate(extracted_info.get("item_changes", [])):

            item_id = item_change.get("item_id")

            changes = item_change.get("changes", {})



            # Check for item attribute resolutions

            for attr, value in list(changes.items()):

                contradiction_id = f"item_{item_id}_{attr}"



                if contradiction_id in resolutions:

                    resolution = resolutions[contradiction_id]



                    if resolution["action"] == "keep_current":

                        # Remove the attribute from changes

                        changes.pop(attr)

                    elif resolution["action"] == "merge":

                        # Update with merged value

                        changes[attr] = resolution["value"]

                    elif resolution["action"] == "accept_new":

                        # Keep the new value (no change needed)

                        pass



                    # Add narrative explanation if available

                    if "narrative" in resolution:

                        if "explanations" not in extracted_info:

                            extracted_info["explanations"] = []



                        extracted_info["explanations"].append({

                            "entity_id": item_id,

                            "attribute": attr,

                            "explanation": resolution["narrative"]

                        })



    def _update_game_state(self, extracted_info: Dict[str, Any]) -> None:

        """

        Update the game state based on extracted information.



        Args:

            extracted_info: Extracted information

        """

        # Process character changes

        for char_change in extracted_info.get("character_changes", []):

            character_id = char_change.get("character_id")

            is_new = char_change.get("is_new", False)



            if is_new:

                # Create new character

                self.card_manager.create_card(

                    "character",

                    char_change.get("name", "Unknown Character"),

                    char_change.get("changes", {})

                )

            else:

                # Update existing character

                self.card_manager.update_card(

                    character_id,

                    char_change.get("changes", {}),

                    "game_event"

                )



        # Process location changes

        for loc_change in extracted_info.get("location_changes", []):

            location_id = loc_change.get("location_id")

            is_new = loc_change.get("is_new", False)



            if is_new:

                # Create new location

                self.card_manager.create_card(

                    "location",

                    loc_change.get("name", "Unknown Location"),

                    loc_change.get("changes", {})

                )

            else:

                # Update existing location

                self.card_manager.update_card(

                    location_id,

                    loc_change.get("changes", {}),

                    "game_event"

                )



        # Process item changes

        for item_change in extracted_info.get("item_changes", []):

            item_id = item_change.get("item_id")

            is_new = item_change.get("is_new", False)



            if is_new:

                # Create new item

                self.card_manager.create_card(

                    "item",

                    item_change.get("name", "Unknown Item"),

                    item_change.get("changes", {})

                )

            else:

                # Update existing item

                self.card_manager.update_card(

                    item_id,

                    item_change.get("changes", {}),

                    "game_event"

                )



        # Process relationship changes

        for rel_change in extracted_info.get("relationship_changes", []):

            entity1_id = rel_change.get("entity1_id")

            entity2_id = rel_change.get("entity2_id")

            relationship_type = rel_change.get("relationship_type", "unspecified")

            strength = rel_change.get("strength", 5)

            emotions = rel_change.get("emotions", {})



            # Create or update relationship

            self.card_manager.create_or_update_relationship(

                entity1_id,

                entity2_id,

                relationship_type,

                strength,

                emotions,

                "game_event"

            )



        # Process story developments

        for story_change in extracted_info.get("story_developments", []):

            story_id = story_change.get("story_id")

            is_new = story_change.get("is_new", False)



            if is_new:

                # Create new story

                self.card_manager.create_card(

                    "story",

                    story_change.get("name", "Unknown Story"),

                    story_change.get("changes", {})

                )

            else:

                # Update existing story

                self.card_manager.update_card(

                    story_id,

                    story_change.get("changes", {}),

                    "game_event"

                )



        # Store memory in vector database

        self._store_memory(extracted_info)



    def _store_memory(self, extracted_info: Dict[str, Any]) -> None:

        """

        Store extracted information as memories in the vector database.



        Args:

            extracted_info: Extracted information

        """

        # Create a memory text from the extracted information

        memory_text = self.information_extractor.summarize_changes(extracted_info)



        if not memory_text:

            return



        # Collect entities involved

        entities = []



        # Add characters

        for char_change in extracted_info.get("character_changes", []):

            char_id = char_change.get("character_id")

            entities.append({

                "id": char_id,

                "type": "character"

            })



        # Add locations

        for loc_change in extracted_info.get("location_changes", []):

            loc_id = loc_change.get("location_id")

            entities.append({

                "id": loc_id,

                "type": "location"

            })



        # Add items

        for item_change in extracted_info.get("item_changes", []):

            item_id = item_change.get("item_id")

            entities.append({

                "id": item_id,

                "type": "item"

            })



        # Add story elements

        for story_change in extracted_info.get("story_developments", []):

            story_id = story_change.get("story_id")

            entities.append({

                "id": story_id,

                "type": "story"

            })



        # Get importance (basic heuristic based on number of changes)

        importance = min(1.0, 0.3 + 0.1 * sum([

            len(extracted_info.get("character_changes", [])),

            len(extracted_info.get("location_changes", [])),

            len(extracted_info.get("item_changes", [])),

            len(extracted_info.get("relationship_changes", [])),

            len(extracted_info.get("story_developments", []))

        ]))



        # Store the memory

        self.vector_store.store_memory(

            memory_text,

            {

                "type": "game_event",

                "timestamp": time.time(),

                "entities": entities,

                "importance": importance,

                "current_focus": extracted_info.get("current_focus", {})

            }

        )



    def _save_interaction_log(self, user_input: str, ai_response: str,

                              extracted_info: Dict[str, Any],

                              contradictions: List[Dict[str, Any]]) -> None:

        """

        Save interaction log to disk.



        Args:

            user_input: User's text input

            ai_response: AI's response

            extracted_info: Extracted information

            contradictions: Detected contradictions

        """

        # Only log if there's meaningful information to save

        if (not extracted_info or len(extracted_info) <= 1) and not contradictions:

            logger.debug("Skipping log save - no significant extracted information")

            return



        # Use integer timestamp for filename to avoid excessive precision

        log_file = os.path.join(self.logs_dir, f"{int(time.time())}.json")



        # Create a streamlined log with only essential information

        log_data = {

            "timestamp": int(time.time()),  # Integer timestamp is sufficient

            "user_input": user_input,

            "ai_response": ai_response

        }



        # Only include extracted_info if there's meaningful content

        if extracted_info and len(extracted_info) > 1:

            log_data["extracted_info"] = extracted_info



        # Only include contradictions if there are any

        if contradictions:

            log_data["contradictions"] = contradictions



        try:

            # Write the file without pretty printing (indent=None) for better performance

            with open(log_file, "w") as f:

                json.dump(log_data, f)

        except Exception as e:

            logger.error(f"Error saving interaction log: {e}")

    def create_new_campaign(self, campaign_name: str, initial_setup=None):
        """
        Create a new campaign.

        Args:
            campaign_name: Name of the campaign
            initial_setup: Optional initial setup data

        Returns:
            True if successful
        """
        try:
            # Set campaign attributes
            self.campaign_id = str(uuid.uuid4())
            self.campaign_name = campaign_name
            self.campaign_dir = os.path.join(CAMPAIGNS_DIR, self.campaign_id)
            self.logs_dir = os.path.join(self.campaign_dir, "logs")

            # Create directories
            os.makedirs(self.campaign_dir, exist_ok=True)
            os.makedirs(self.logs_dir, exist_ok=True)

            # Make sure card manager is initialized with new campaign ID
            self.card_manager = CardManager(self.campaign_id)

            # Initialize empty session history and basic context
            self.session_history = []
            self.current_context = "Game is starting."

            # Initialize empty focus
            self.current_focus = {
                "characters": [],
                "location": None,
                "items": []
            }

            # Save metadata
            self._save_campaign_metadata()

            # Add initial content if provided
            if initial_setup:
                # Create locations first
                location_ids = {}
                for i, loc_data in enumerate(initial_setup.get("locations", [])):
                    loc_id = self.card_manager.create_card(
                        "location",
                        loc_data.get("name", "Unknown Location"),
                        loc_data
                    )
                    location_ids[str(i)] = loc_id

                # Create characters
                character_ids = {}
                for i, char_data in enumerate(initial_setup.get("characters", [])):
                    # Update location reference
                    if "location" in char_data and char_data["location"] in location_ids:
                        char_data["location"] = location_ids[char_data["location"]]

                    char_id = self.card_manager.create_card(
                        "character",
                        char_data.get("name", "Unknown Character"),
                        char_data
                    )
                    character_ids[str(i)] = char_id

                # Create items
                item_ids = {}
                for i, item_data in enumerate(initial_setup.get("items", [])):
                    # Update location reference
                    if "location" in item_data and item_data["location"] in location_ids:
                        item_data["location"] = location_ids[item_data["location"]]

                    item_id = self.card_manager.create_card(
                        "item",
                        item_data.get("name", "Unknown Item"),
                        item_data
                    )
                    item_ids[str(i)] = item_id

                # Set initial focus
                if "initial_focus" in initial_setup:
                    focus = initial_setup["initial_focus"]

                    # Set characters
                    if "characters" in focus:
                        self.current_focus["characters"] = [
                            character_ids.get(char_ref, char_ref)
                            for char_ref in focus["characters"]
                            if char_ref in character_ids
                        ]

                    # Set location
                    if "location" in focus and focus["location"] in location_ids:
                        self.current_focus["location"] = location_ids[focus["location"]]

                    # Set items
                    if "items" in focus:
                        self.current_focus["items"] = [
                            item_ids.get(item_ref, item_ref)
                            for item_ref in focus["items"]
                            if item_ref in item_ids
                        ]

                # Save updated metadata
                self._save_campaign_metadata()

            return True
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return False

    def load_campaign(self, campaign_id=None):
        """
        Load an existing campaign.

        Args:
            campaign_id: Optional ID of the campaign to load. If None, shows selection dialog.

        Returns:
            True if campaign was loaded successfully, False otherwise
        """
        # If no campaign_id provided, show selection dialog
        if campaign_id is None:
            from rpg_gui import CampaignSelectionDialog
            campaign_dialog = CampaignSelectionDialog(self, self)
            if campaign_dialog.exec_() == QDialog.Accepted:
                campaign_id = campaign_dialog.selected_campaign_id
            else:
                return False

        if not campaign_id:
            logger.error("No campaign ID provided or selected")
            return False

        # IMPORTANT: Reset session state
        self.session_history = []
        self.current_context = "Game is starting."
        self.current_focus = {
            "characters": [],
            "location": None,
            "items": []
        }
        self._cached_context = None

        # Set campaign paths
        self.campaign_id = campaign_id
        self.campaign_dir = os.path.join(CAMPAIGNS_DIR, campaign_id)
        self.cards_dir = os.path.join(self.campaign_dir, "cards")
        self.logs_dir = os.path.join(self.campaign_dir, "logs")

        # Ensure directories exist
        os.makedirs(self.campaign_dir, exist_ok=True)
        os.makedirs(self.cards_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Reset card manager and other components
        self.card_manager = CardManager(campaign_id)
        self.vector_store = VectorStore(campaign_id)
        self.information_extractor = InformationExtractor(self.llm, self.card_manager)
        self.context_assembler = ContextAssembler(self.card_manager, self.vector_store)
        self.contradiction_detector = ContradictionDetector(self.llm, self.card_manager)

        # Load metadata and session history for this specific campaign
        self._load_campaign_metadata()

        # Check and repair focus references
        self._verify_focus_references()

        logger.info(f"Loaded campaign: {self.campaign_name} ({campaign_id})")
        return True

    def delete_campaign(self, campaign_id):
        """
        Delete a campaign and all its associated data.

        Args:
            campaign_id: ID of the campaign to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        import shutil

        # Check if this is the currently loaded campaign
        is_current = hasattr(self, 'memory_system') and self.memory_system.campaign_id == campaign_id

        try:
            # Get campaign directory
            campaign_dir = os.path.join(CAMPAIGNS_DIR, campaign_id)

            # Check if directory exists
            if not os.path.exists(campaign_dir):
                logger.error(f"Campaign directory not found: {campaign_dir}")
                return False

            # Delete the directory and all its contents
            shutil.rmtree(campaign_dir)

            logger.info(f"Deleted campaign: {campaign_id}")

            # If this was the current campaign, reset the UI
            if is_current:
                # Clear UI
                if hasattr(self, 'game_display'):
                    self.game_display.clear()
                    self.characters_list.clear()
                    self.locations_list.clear()
                    self.items_list.clear()

                    # Reset info panels
                    self.character_info.update_info(None)
                    self.location_info.update_info(None, None)

                    # Show message in game display
                    self.game_display.setHtml(
                        '<div style="color: #FF5555; font-size: 18px; font-weight: bold; margin: 20px;">'
                        'The current campaign has been deleted.<br><br>'
                        'Please create a new campaign or load an existing one.'
                        '</div>'
                    )

                # Show dialog to create or load campaign
                QMessageBox.information(
                    self,
                    "Campaign Deleted",
                    "The current campaign has been deleted. You'll need to create a new campaign or load an existing one."
                )

                # Reset memory system (create a blank one)
                self.memory_system = MemorySystem(llm_interface=self.memory_system.llm)

                # Show campaign selection
                self.select_campaign()

            return True
        except Exception as e:
            logger.error(f"Error deleting campaign {campaign_id}: {e}")
            return False


    def _verify_focus_references(self) -> None:

        """

        Verify that the current focus references valid entities and repair if needed.

        """

        if not self.current_focus:

            logger.warning("Current focus is empty, initializing default focus")

            self.current_focus = {"characters": [], "location": None, "items": []}

            return



        # Check characters

        valid_characters = []

        for char_id in self.current_focus.get("characters", []):

            if self.card_manager.get_card(char_id):

                valid_characters.append(char_id)

            else:

                logger.warning(f"Removing invalid character reference from focus: {char_id}")



        # Check location

        location_id = self.current_focus.get("location")

        if location_id and not self.card_manager.get_card(location_id):

            logger.warning(f"Removing invalid location reference from focus: {location_id}")

            location_id = None



        # Check items

        valid_items = []

        for item_id in self.current_focus.get("items", []):

            if self.card_manager.get_card(item_id):

                valid_items.append(item_id)

            else:

                logger.warning(f"Removing invalid item reference from focus: {item_id}")



        # Fix focus

        fixed_focus = {

            "characters": valid_characters,

            "location": location_id,

            "items": valid_items

        }



        # If focus had invalid references, rebuild it

        if (valid_characters != self.current_focus.get("characters", []) or

            location_id != self.current_focus.get("location") or

            valid_items != self.current_focus.get("items", [])):



            logger.warning("Focus contained invalid references, fixed focus: {fixed_focus}")

            self.current_focus = fixed_focus



            # Initialize with defaults if we have no valid focus

            if not location_id and not valid_characters:

                self._initialize_default_focus()



        # Save the fixed metadata

        self._save_campaign_metadata()



    def _initialize_default_focus(self) -> None:

        """

        Initialize default focus if none valid exists.

        """

        logger.info("Initializing default focus")



        # Find first available location

        locations = self.card_manager.get_cards_by_type("location")

        if locations:

            first_location_id = next(iter(locations.keys()))

            self.current_focus["location"] = first_location_id

            logger.info(f"Set default location: {first_location_id}")



            # Find characters at this location

            chars_at_location = self.card_manager.get_character_at_location(first_location_id)

            if chars_at_location:

                self.current_focus["characters"] = [char.id for char in chars_at_location]

                logger.info(f"Added {len(chars_at_location)} characters at location to focus")

        else:

            # No locations, use first available character

            characters = self.card_manager.get_cards_by_type("character")

            if characters:

                first_char_id = next(iter(characters.keys()))

                self.current_focus["characters"] = [first_char_id]

                logger.info(f"No locations found, set focus to character: {first_char_id}")



    def verify_campaign_integrity(self) -> Dict[str, Any]:

        """

        Verify the integrity of the campaign data.



        Returns:

            Dictionary with verification results

        """

        results = {

            "characters": {"count": 0, "valid": 0, "issues": []},

            "locations": {"count": 0, "valid": 0, "issues": []},

            "items": {"count": 0, "valid": 0, "issues": []},

            "stories": {"count": 0, "valid": 0, "issues": []},

            "relationships": {"count": 0, "valid": 0, "issues": []},

            "focus": {"valid": False, "issues": []}

        }



        # Check card references

        for card_type in results.keys():

            if card_type == "focus":

                continue



            # Get singular type for dictionary keys

            singular_type = card_type[:-1] if card_type.endswith('s') else card_type



            # Count cards

            cards = self.card_manager.cards_by_type.get(singular_type, {})

            results[card_type]["count"] = len(cards)



            # Check each card

            for card_id, card in cards.items():

                try:

                    # Basic validation - can we get a dict representation?

                    card_dict = card.to_dict()

                    if not isinstance(card_dict, dict):

                        results[card_type]["issues"].append(f"Card {card_id} has invalid to_dict output")

                        continue



                    # Check required fields

                    required_fields = ["id", "type", "name"]

                    missing_fields = [field for field in required_fields if field not in card_dict]

                    if missing_fields:

                        results[card_type]["issues"].append(

                            f"Card {card_id} missing required fields: {', '.join(missing_fields)}"

                        )

                        continue



                    # Card is considered valid

                    results[card_type]["valid"] += 1



                except Exception as e:

                    results[card_type]["issues"].append(f"Error processing card {card_id}: {str(e)}")



        # Check current focus

        if self.current_focus:

            # Check character references

            for char_id in self.current_focus.get("characters", []):

                if not self.card_manager.get_card(char_id):

                    results["focus"]["issues"].append(f"Focus references non-existent character: {char_id}")



            # Check location reference

            loc_id = self.current_focus.get("location")

            if loc_id and not self.card_manager.get_card(loc_id):

                results["focus"]["issues"].append(f"Focus references non-existent location: {loc_id}")



            # Check item references

            for item_id in self.current_focus.get("items", []):

                if not self.card_manager.get_card(item_id):

                    results["focus"]["issues"].append(f"Focus references non-existent item: {item_id}")



            # Focus is valid if there are no issues

            results["focus"]["valid"] = len(results["focus"]["issues"]) == 0

        else:

            results["focus"]["issues"].append("No current focus set")



        return results



    def get_campaign_summary(self) -> Dict[str, Any]:

        """

        Get a summary of the current campaign.



        Returns:

            Campaign summary

        """

        # Count entities

        character_count = len(self.card_manager.cards_by_type.get("character", {}))

        location_count = len(self.card_manager.cards_by_type.get("location", {}))

        item_count = len(self.card_manager.cards_by_type.get("item", {}))

        story_count = len(self.card_manager.cards_by_type.get("story", {}))

        relationship_count = len(self.card_manager.cards_by_type.get("relationship", {}))



        # Get active characters

        active_characters = []

        for char_id, character in self.card_manager.cards_by_type.get("character", {}).items():

            if hasattr(character, "status") and character.status == "active":

                active_characters.append({

                    "id": char_id,

                    "name": character.name,

                    "description": character.description

                })



        # Get active stories

        active_stories = []

        for story in self.card_manager.get_active_stories():

            active_stories.append({

                "id": story.id,

                "name": story.name,

                "description": story.description

            })



        # Get current location

        current_location = None

        if self.current_focus.get("location"):

            location = self.card_manager.get_card(self.current_focus["location"])

            if location:

                current_location = {

                    "id": location.id,

                    "name": location.name,

                    "description": location.description

                }



        return {

            "id": self.campaign_id,

            "name": self.campaign_name,

            "stats": {

                "characters": character_count,

                "locations": location_count,

                "items": item_count,

                "stories": story_count,

                "relationships": relationship_count,

                "interactions": len(self.session_history)

            },

            "active_characters": active_characters,

            "active_stories": active_stories,

            "current_location": current_location,

            "current_focus": self.current_focus

        }



    def get_entity_details(self, entity_id: str) -> Optional[Dict[str, Any]]:

        """

        Get detailed information about an entity.



        Args:

            entity_id: ID of the entity



        Returns:

            Entity details, or None if not found

        """

        entity = self.card_manager.get_card(entity_id)



        if not entity:

            return None



        # Get entity relationships

        relationships = []

        for rel in self.card_manager.get_relationships_for_entity(entity_id):

            other_id = rel.entity2 if rel.entity1 == entity_id else rel.entity1

            other_entity = self.card_manager.get_card(other_id)



            relationships.append({

                "id": rel.id,

                "with": {

                    "id": other_id,

                    "name": other_entity.name if other_entity else other_id,

                    "type": other_entity.type if other_entity else "unknown"

                },

                "type": rel.relationship_type,

                "strength": rel.strength,

                "emotions": rel.emotions

            })



        # Get entity memories

        memories = self.vector_store.search_similar(

            entity.name,

            top_k=10,

            filter_conditions={"entities": [entity_id]}

        )



        # Convert to dict for JSON serialization

        entity_dict = entity.to_dict()



        return {

            "entity": entity_dict,

            "relationships": relationships,

            "memories": memories

        }



    def run_consistency_check(self) -> Dict[str, Any]:

        """

        Run a comprehensive consistency check on the game state.



        Returns:

            Results of the consistency check

        """

        inconsistencies = self.contradiction_detector.run_consistency_check()



        # Group inconsistencies by type

        grouped = {}

        for inconsistency in inconsistencies:

            type_key = inconsistency.get("type", "other")

            if type_key not in grouped:

                grouped[type_key] = []



            grouped[type_key].append(inconsistency)



        # Count by severity

        severity_counts = {

            "high": 0,

            "medium": 0,

            "low": 0

        }



        for inconsistency in inconsistencies:

            severity = inconsistency.get("severity", "medium")

            severity_counts[severity] = severity_counts.get(severity, 0) + 1



        return {

            "inconsistencies": inconsistencies,

            "grouped": grouped,

            "counts": {

                "total": len(inconsistencies),

                "by_type": {type_key: len(items) for type_key, items in grouped.items()},

                "by_severity": severity_counts

            }

        }



    def get_available_campaigns(self) -> List[Dict[str, Any]]:

        """

        Get a list of available campaigns.



        Returns:

            List of available campaigns

        """

        campaigns = []



        if os.path.exists(CAMPAIGNS_DIR):

            for campaign_id in os.listdir(CAMPAIGNS_DIR):

                campaign_dir = os.path.join(CAMPAIGNS_DIR, campaign_id)



                if os.path.isdir(campaign_dir):

                    # Try to load campaign metadata

                    metadata_path = os.path.join(campaign_dir, "campaign_metadata.json")



                    if os.path.exists(metadata_path):

                        try:

                            with open(metadata_path, "r") as f:

                                metadata = json.load(f)



                                campaigns.append({

                                    "id": campaign_id,

                                    "name": metadata.get("name", "Unknown Campaign"),

                                    "created": metadata.get("created", 0),

                                    "last_modified": metadata.get("last_modified", 0)

                                })

                        except Exception as e:

                            logger.error(f"Error loading campaign metadata: {e}")



                            # Add with minimal information

                            campaigns.append({

                                "id": campaign_id,

                                "name": "Unknown Campaign",

                                "created": 0,

                                "last_modified": 0

                            })



        # Sort by last modified time (descending)

        campaigns.sort(key=lambda x: x.get("last_modified", 0), reverse=True)



        return campaigns