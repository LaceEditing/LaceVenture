import sys
import random
import os

import re

import hashlib

import json

import glob

from functools import lru_cache

import json

import requests

from typing import Any, Dict, List, Optional, Union, Iterator



from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,

                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel,

                             QComboBox, QListWidget, QMessageBox, QFormLayout, QSpinBox,

                             QSplitter, QScrollArea, QFrame, QDialog, QDialogButtonBox,

                             QCheckBox, QTextBrowser, QGroupBox, QSlider)

from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject



# Import your existing game logic - adjust import paths as needed

# We're assuming the rpg_engine.py file is in the same directory

import rpg_engine



# Constants - Lavender Theme

SYSTEM_COLOR = "#6A4C93"  # Darkened deep lavender for better contrast

DM_NAME_COLOR = "#7E57C2"  # Darkened medium lavender

DM_TEXT_COLOR = "#5D4777"  # Darkened light lavender for better readability

PLAYER_COLOR = "#9C3587"  # Darker purple/pink

HIGHLIGHT_COLOR = "#4A2D7D"  # Darker purple for highlights

BG_COLOR = "#F5F0FF"  # Light lavender background

ACCENT_COLOR = "#8046CC"  # Darker accent color for buttons





class StreamingTextDisplay(QTextEdit):

    """Widget for displaying streaming text with typewriter effect"""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setReadOnly(True)

        self.setMinimumHeight(300)



        # Create text formats with the lavender colors

        self.system_format = QTextCharFormat()

        self.system_format.setForeground(QColor(SYSTEM_COLOR))

        self.system_format.setFontWeight(QFont.Weight.Bold)  # Make system messages bold



        self.dm_name_format = QTextCharFormat()

        self.dm_name_format.setForeground(QColor(DM_NAME_COLOR))

        self.dm_name_format.setFontWeight(QFont.Weight.Bold)



        self.dm_text_format = QTextCharFormat()

        self.dm_text_format.setForeground(QColor(DM_TEXT_COLOR))



        self.player_format = QTextCharFormat()

        self.player_format.setForeground(QColor(PLAYER_COLOR))

        self.player_format.setFontWeight(QFont.Weight.Bold)  # Make player input bold



        # Set a default font size

        default_font = self.font()

        default_font.setPointSize(12)  # Larger font for better readability

        self.setFont(default_font)



    def append_system_message(self, text):

        """Add a system message with styled text"""

        cursor = self.textCursor()

        cursor.movePosition(QTextCursor.MoveOperation.End)

        cursor.insertText(text + "\n", self.system_format)

        self.setTextCursor(cursor)

        self.ensureCursorVisible()



    def append_dm_message(self, text):

        """Add a DM message with styled text"""

        cursor = self.textCursor()

        cursor.movePosition(QTextCursor.MoveOperation.End)

        cursor.insertText("DM: ", self.dm_name_format)

        cursor.insertText(text + "\n", self.dm_text_format)

        self.setTextCursor(cursor)

        self.ensureCursorVisible()



    def append_player_message(self, text):

        """Add a player message with styled text"""

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
        self.repetition_detector = RepetitionDetector(threshold=0.6, memory_size=5)

        # Get last response from conversation history if available
        self.last_response = None
        if 'context' in prompt_vars:
            # Try to extract the last DM response from the context
            context_lines = prompt_vars['context'].split('\n')
            for line in reversed(context_lines):
                if line.startswith("DM:"):
                    self.last_response = line[3:].strip()
                    break

    def extract_key_phrases(self, text, num_phrases=3):
        """Extract a few distinctive phrases from the text to highlight what to avoid"""
        # Simple extraction of 2-3 word phrases
        words = text.split()
        if len(words) < 4:
            return text

        # Get some random 2-3 word phrases
        phrases = []
        for _ in range(min(num_phrases, len(words) // 3)):
            start = random.randint(0, len(words) - 3)
            length = random.randint(2, 3)
            phrase = " ".join(words[start:start + length])
            phrases.append(phrase)

        return ", ".join(phrases)

    def enhance_prompt_for_variety(self, base_prompt, previous_response=None):
        """Add anti-repetition instructions to the prompt"""
        variety_instructions = """
        ADDITIONAL ANTI-REPETITION REQUIREMENTS:
        - AVOID ALL REPETITION: Do not reuse words, phrases, or sentence structures from your previous responses
        - VARIETY IS ESSENTIAL: Use completely different descriptive language than you've used before
        - FRESH PERSPECTIVES: Describe scenes and characters from new angles and perspectives
        - DIVERSE VOCABULARY: Consciously use vocabulary that hasn't appeared in recent exchanges
        - NEW SENSORY DETAILS: Focus on different senses (sound, smell, touch) than in previous descriptions
        - ALTERNATIVE NARRATIVE STYLES: Vary between direct description, metaphorical language, and dialogue
        - DOUBLE CHECK BEFORE OUTPUT: Before pasting your output, please ensure that the repetition has been resolved
        """

        if previous_response:
            key_phrases = self.extract_key_phrases(previous_response)
            if key_phrases:
                variety_instructions += f"""
                IMPORTANT: Your last response used phrases like "{key_phrases}". 
                DO NOT use these words or similar phrasings again. Find completely new ways to express yourself.
                """

        # Insert these instructions in an appropriate place in the base prompt
        # For example, after the "CRITICAL OUTPUT REQUIREMENTS" section
        insertion_point = "CRITICAL OUTPUT REQUIREMENTS:"
        parts = base_prompt.split(insertion_point)

        if len(parts) == 2:
            enhanced_prompt = parts[0] + insertion_point + parts[1].split("\n", 1)[
                0] + "\n" + variety_instructions + "\n" + parts[1].split("\n", 1)[1]
            return enhanced_prompt

        # Fallback: just append the instructions
        return base_prompt + "\n" + variety_instructions

    def adjust_params_for_variety(self, repetition_score, base_temp=0.7, max_temp=1.2):
        """Calculate adjusted temperature based on repetition score"""
        # Scale between base_temp and max_temp based on repetition score
        if repetition_score > 0.5:
            # The more repetitive, the higher the temperature
            adjusted_temp = min(base_temp + (repetition_score - 0.5) * 2 * (max_temp - base_temp), max_temp)
            return adjusted_temp
        return base_temp

    def run(self):
        """Run the model generation with anti-repetition mechanisms"""
        try:
            # Get response length from game state if available
            response_length = 3  # Default medium
            if 'game_info' in self.prompt_vars and 'response_length' in self.prompt_vars['game_info']:
                response_length = self.prompt_vars['game_info']['response_length']

            # Define response length instructions
            response_length_instructions = {
                1: "EXTREMELY BRIEF: Keep responses very short, 1-2 sentences maximum. Be direct and to the point.",
                2: "BRIEF: Keep responses concise, 2-3 sentences maximum. Include only essential details.",
                3: "MEDIUM: Use a balanced length for responses, 4-6 sentences. Include moderate description.",
                4: "DETAILED: Provide detailed responses with rich descriptions, 7-10 sentences. Elaborate on surroundings and emotions.",
                5: "VERY DETAILED: Be highly detailed and descriptive in responses, 11+ sentences. Use vivid, immersive descriptions and elaborate on all sensory details."
            }

            # Format the basic prompt with response length instructions
            formatted_prompt = f"""
    You are an experienced Dungeon Master for a {self.prompt_vars['genre']} RPG set in {self.prompt_vars['world_name']}. Your role is to:

    1. Create an immersive world that maintains cohesiveness and coherence
    2. Portray NPCs with consistent personalities, goals, and knowledge
    3. Present appropriate challenges and opportunities for character development
    4. Maintain narrative continuity and remember details from previous sessions
    5. Apply game rules fairly while prioritizing storytelling and player enjoyment
    6. Adapt the story based on player choices to create a truly interactive experience
    7. Always speak in character or as a narrator, never interject from the role of an AI Language Model or with your own opinions

    CRITICAL OUTPUT REQUIREMENTS:
    - {response_length_instructions.get(response_length, response_length_instructions[3])}
    - VARIETY: Never use similar sentence structures back-to-back
    - PRECISION: Use specific, brief details rather than general description or long drawn out paragraphs
    - UNIQUENESS: Avoid reusing phrases, descriptions, or scene transitions
    - FREEDOM: Only give the player specific choices when absolutely necessary, otherwise always simply ask "What will you do?" to end your output
    - GAMEPLAY: The player character should never speak on their own, unless the user tells them to in their responses. You will never generate dialogue from their perspective
    - ROLE CONSISTENCY: Always respond in role as the Dungeon Master or as an NPC character when speaking. Never break character to respond as an AI model. Never mention AI models, prompts, or language processing. Stay completely immersed in the fantasy role.
    - FORBIDDEN PHRASES: Never use phrases like "I can't create content that is...", "As an AI, I...", "I'm sorry, but I cannot...", or any similar statements that break immersion.
    - NARRATIVE VOICE: When describing scenes, use the voice of a storyteller. When NPCs speak, use their established personalities and dialogue patterns.
    - REPETITION PREVENTION: Don't output anything until you've ensured that the entirety of your output is concise and lacking repetition
    - FINISHING OUTPUT: Always end your output, no matter what it is, with "What will you do?"

    CONTENT RATING GUIDELINES - THIS STORY HAS A "{self.prompt_vars['rating']}" RATING:
    - E rating: Keep content family-friendly. Avoid graphic violence, frightening scenarios, sexual content, and strong language.
    - T rating: Moderate content is acceptable. Some violence, dark themes, mild language, and light romantic implications allowed, but nothing explicit or graphic.
    - M rating: Mature content is permitted. You may include graphic violence, sexual themes, intense scenarios, and strong language as appropriate to the story.

    PLOT PACING GUIDELINES - THIS STORY HAS A "{self.prompt_vars['plot_pace']}" PACING:
    - Fast-paced: Maintain steady forward momentum with regular plot developments and challenges. Focus primarily on action, goals, and advancing the main storyline. Character development should happen through significant events rather than quiet moments. Keep the story moving forward with new developments in most scenes.
    - Balanced: Create a rhythm alternating between plot advancement and character moments. Allow time for reflection and relationship development between significant story beats. Mix everyday interactions with moderate plot advancement. Ensure characters have time to process events before introducing new major developments.
    - Slice-of-life: Deliberately slow down plot progression in favor of everyday moments and mundane interactions. Focus on character relationships, personal growth, and daily activities rather than dramatic events. Allow extended periods where characters simply live their lives, with minimal story progression. Prioritize small, meaningful character moments and ordinary situations. Major plot developments should be rare and spaced far apart, with emphasis on how characters experience their everyday world.

    DYNAMIC WORLD CREATION:
    You are expected to actively create new elements to build a rich, evolving world.

    The adventure takes place in a {self.prompt_vars['setting_description']}. The tone is {self.prompt_vars['tone']}.

    Current game state:
    {self.prompt_vars['context']}

    Player: {self.prompt_vars['question']}
    """
            # Enhance the prompt with anti-repetition instructions
            if self.last_response:
                formatted_prompt = self.enhance_prompt_for_variety(formatted_prompt, self.last_response)
            else:
                formatted_prompt = self.enhance_prompt_for_variety(formatted_prompt)

            # Check repetition level of last few responses
            repetition_score = 0
            if self.last_response:
                repetition_score = self.repetition_detector.get_repetition_score(self.last_response)

            # Adjust temperature based on repetition
            original_temp = self.model.temperature
            if repetition_score > 0.5:
                adjusted_temp = self.adjust_params_for_variety(repetition_score,
                                                               base_temp=original_temp,
                                                               max_temp=min(original_temp + 0.5, 1.2))
                print(f"Increasing temperature from {original_temp} to {adjusted_temp} due to repetition")
                self.model.update_settings(temperature=adjusted_temp)

            # Generate the response
            try:
                # Stream the response token by token
                for chunk in self.model.stream(formatted_prompt):
                    self.text_generated.emit(chunk)
                    self.full_response += chunk
            except Exception as stream_error:
                print(f"Streaming error: {stream_error}")
                # Fall back to standard generation
                self.full_response = self.model.invoke(formatted_prompt)
                self.text_generated.emit(self.full_response)

            # Restore original temperature
            if repetition_score > 0.5:
                self.model.update_settings(temperature=original_temp)

            # Add this response to the repetition detector
            self.repetition_detector.add_response(self.full_response)

        except Exception as e:
            error_msg = f"\nError generating response: {str(e)}"
            print(error_msg)
            self.text_generated.emit(error_msg)

        # Signal that generation is complete
        self.generation_complete.emit(self.full_response)


class StoryCreationWizard(QWidget):

    """Wizard for creating a new story"""



    story_created = pyqtSignal(dict)



    def __init__(self, parent=None):

        super().__init__(parent)

        self.player_input = {}

        self.npcs = []

        self.setup_ui()



    def setup_ui(self):

        """Set up the UI components with improved layout"""

        layout = QVBoxLayout(self)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(25)  # More space between sections



        # Create a scroll area to contain all form elements

        scroll_area = QScrollArea()

        scroll_area.setWidgetResizable(True)

        scroll_area.setFrameShape(QFrame.Shape.NoFrame)



        scroll_content = QWidget()

        scroll_layout = QVBoxLayout(scroll_content)

        scroll_layout.setContentsMargins(10, 10, 10, 10)

        scroll_layout.setSpacing(25)



        # Create section headers style

        section_style = f"""

            font-size: 16px;

            font-weight: bold;

            color: {ACCENT_COLOR};

            padding: 5px;

            border-bottom: 1px solid {DM_NAME_COLOR};

            margin-top: 15px;

        """



        # Basic Story Info Section

        basic_info_header = QLabel("Story Information")

        basic_info_header.setStyleSheet(section_style)

        scroll_layout.addWidget(basic_info_header)



        basic_info_form = QWidget()

        basic_info_layout = QFormLayout(basic_info_form)

        basic_info_layout.setVerticalSpacing(15)  # More space between form items

        basic_info_layout.setHorizontalSpacing(20)

        basic_info_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        basic_info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # Model selection

        model_label = QLabel("AI Model:")

        model_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.model_combo = QComboBox()

        available_models = rpg_engine.get_available_ollama_models()

        self.model_combo.addItems(available_models)

        basic_info_layout.addRow(model_label, self.model_combo)



        # Story title

        title_label = QLabel("Story Title:")

        title_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.title_input = QLineEdit()

        basic_info_layout.addRow(title_label, self.title_input)



        # World name

        world_label = QLabel("World Name:")

        world_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.world_input = QLineEdit()

        basic_info_layout.addRow(world_label, self.world_input)



        # Genre

        genre_label = QLabel("Genre:")

        genre_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.genre_input = QLineEdit()

        basic_info_layout.addRow(genre_label, self.genre_input)



        # Setting

        setting_label = QLabel("Setting Description:")

        setting_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.setting_input = QTextEdit()

        self.setting_input.setMinimumHeight(100)

        basic_info_layout.addRow(setting_label, self.setting_input)



        # Tone

        tone_label = QLabel("Tone:")

        tone_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.tone_input = QLineEdit()

        basic_info_layout.addRow(tone_label, self.tone_input)



        # Content rating

        rating_label = QLabel("Content Rating:")

        rating_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.rating_combo = QComboBox()

        self.rating_combo.addItems(["E - Family Friendly", "T - Teen", "M - Mature"])

        basic_info_layout.addRow(rating_label, self.rating_combo)



        # Plot pacing

        pacing_label = QLabel("Plot Pacing:")

        pacing_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.pacing_combo = QComboBox()

        self.pacing_combo.addItems(["Fast-paced", "Balanced", "Slice-of-life"])

        basic_info_layout.addRow(pacing_label, self.pacing_combo)



        scroll_layout.addWidget(basic_info_form)



        # Character Section

        character_header = QLabel("Character Information")

        character_header.setStyleSheet(section_style)

        scroll_layout.addWidget(character_header)



        character_form = QWidget()

        character_layout = QFormLayout(character_form)

        character_layout.setVerticalSpacing(15)

        character_layout.setHorizontalSpacing(20)

        character_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        character_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # Character name

        char_name_label = QLabel("Character Name:")

        char_name_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.character_name_input = QLineEdit()

        character_layout.addRow(char_name_label, self.character_name_input)



        # Character race

        char_race_label = QLabel("Character Race:")

        char_race_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.character_race_input = QLineEdit()

        character_layout.addRow(char_race_label, self.character_race_input)



        # Character class

        char_class_label = QLabel("Character Class:")

        char_class_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.character_class_input = QLineEdit()

        character_layout.addRow(char_class_label, self.character_class_input)



        # Character traits

        char_traits_label = QLabel("Character Traits:")

        char_traits_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.character_traits_input = QLineEdit()

        self.character_traits_input.setPlaceholderText("Comma separated")

        character_layout.addRow(char_traits_label, self.character_traits_input)



        # Character abilities

        char_abilities_label = QLabel("Character Abilities:")

        char_abilities_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.character_abilities_input = QLineEdit()

        self.character_abilities_input.setPlaceholderText("Comma separated")

        character_layout.addRow(char_abilities_label, self.character_abilities_input)



        scroll_layout.addWidget(character_form)



        # Location Section

        location_header = QLabel("Location Information")

        location_header.setStyleSheet(section_style)

        scroll_layout.addWidget(location_header)



        location_form = QWidget()

        location_layout = QFormLayout(location_form)

        location_layout.setVerticalSpacing(15)

        location_layout.setHorizontalSpacing(20)

        location_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        location_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # Starting location name

        loc_name_label = QLabel("Starting Location Name:")

        loc_name_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.location_name_input = QLineEdit()

        location_layout.addRow(loc_name_label, self.location_name_input)



        # Starting location description

        loc_desc_label = QLabel("Starting Location Description:")

        loc_desc_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.location_desc_input = QTextEdit()

        self.location_desc_input.setMinimumHeight(100)

        location_layout.addRow(loc_desc_label, self.location_desc_input)



        scroll_layout.addWidget(location_form)



        # Quest Section

        quest_header = QLabel("Quest Information")

        quest_header.setStyleSheet(section_style)

        scroll_layout.addWidget(quest_header)



        quest_form = QWidget()

        quest_layout = QFormLayout(quest_form)

        quest_layout.setVerticalSpacing(15)

        quest_layout.setHorizontalSpacing(20)

        quest_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        quest_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # Quest name

        quest_name_label = QLabel("Initial Quest Name:")

        quest_name_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.quest_name_input = QLineEdit()

        quest_layout.addRow(quest_name_label, self.quest_name_input)



        # Quest description

        quest_desc_label = QLabel("Initial Quest Description:")

        quest_desc_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.quest_desc_input = QTextEdit()

        self.quest_desc_input.setMinimumHeight(100)

        quest_layout.addRow(quest_desc_label, self.quest_desc_input)



        # World facts

        facts_label = QLabel("World Facts:")

        facts_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.world_facts_input = QTextEdit()

        self.world_facts_input.setMinimumHeight(100)

        self.world_facts_input.setPlaceholderText("One fact per line")

        quest_layout.addRow(facts_label, self.world_facts_input)



        scroll_layout.addWidget(quest_form)



        # NPCs Section

        npc_header = QLabel("NPCs (Optional)")

        npc_header.setStyleSheet(section_style)

        scroll_layout.addWidget(npc_header)



        # NPCs list with label

        npcs_list_label = QLabel("Added NPCs:")

        npcs_list_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        scroll_layout.addWidget(npcs_list_label)



        self.npcs_list = QListWidget()

        self.npcs_list.setMaximumHeight(150)

        self.npcs_list.setStyleSheet(f"""

            QListWidget {{

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 5px;

                padding: 5px;

                color: {HIGHLIGHT_COLOR};

            }}

            QListWidget::item {{ padding: 5px; }}

            QListWidget::item:selected {{ 

                background-color: {DM_NAME_COLOR}; 

                color: white; 

            }}

        """)

        scroll_layout.addWidget(self.npcs_list)



        # NPC Form

        npc_form = QGroupBox("Add New NPC")

        npc_form.setStyleSheet(f"""

            QGroupBox {{ 

                border: 1px solid {DM_NAME_COLOR}; 

                border-radius: 8px; 

                margin-top: 12px; 

                padding: 15px;

                background-color: #F0E8FF;

            }}

            QGroupBox::title {{ 

                color: {HIGHLIGHT_COLOR}; 

                subcontrol-origin: margin;

                left: 10px;

                padding: 0 5px 0 5px;

                font-weight: bold;

            }}

        """)

        npc_form_layout = QFormLayout(npc_form)

        npc_form_layout.setVerticalSpacing(15)

        npc_form_layout.setHorizontalSpacing(20)

        npc_form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        npc_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # NPC name

        npc_name_label = QLabel("NPC Name:")

        npc_name_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_name_input = QLineEdit()

        npc_form_layout.addRow(npc_name_label, self.npc_name_input)



        # NPC race

        npc_race_label = QLabel("NPC Race:")

        npc_race_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_race_input = QLineEdit()

        npc_form_layout.addRow(npc_race_label, self.npc_race_input)



        # NPC description

        npc_desc_label = QLabel("NPC Description:")

        npc_desc_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_desc_input = QTextEdit()

        self.npc_desc_input.setMaximumHeight(80)

        npc_form_layout.addRow(npc_desc_label, self.npc_desc_input)



        # NPC disposition

        npc_disp_label = QLabel("NPC Disposition:")

        npc_disp_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_disposition_input = QLineEdit()

        npc_disposition_info = QLabel("(friendly, hostile, neutral)")

        npc_disposition_info.setStyleSheet("color: gray; font-style: italic;")

        disp_layout = QHBoxLayout()

        disp_layout.addWidget(self.npc_disposition_input)

        disp_layout.addWidget(npc_disposition_info)

        npc_form_layout.addRow(npc_disp_label, disp_layout)



        # NPC motivation

        npc_motiv_label = QLabel("NPC Motivation:")

        npc_motiv_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_motivation_input = QLineEdit()

        npc_form_layout.addRow(npc_motiv_label, self.npc_motivation_input)



        # NPC dialogue style

        npc_dialogue_label = QLabel("NPC Dialogue Style:")

        npc_dialogue_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.npc_dialogue_input = QLineEdit()

        npc_form_layout.addRow(npc_dialogue_label, self.npc_dialogue_input)



        # Add NPC button

        self.add_npc_button = QPushButton("Add NPC")

        self.add_npc_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

                min-width: 120px;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.add_npc_button.clicked.connect(self.add_npc)

        npc_form_layout.addRow("", self.add_npc_button)



        scroll_layout.addWidget(npc_form)



        # Set the scroll content

        scroll_area.setWidget(scroll_content)

        layout.addWidget(scroll_area, 1)  # Give it stretch priority



        # Navigation buttons

        nav_layout = QHBoxLayout()

        nav_layout.setSpacing(20)



        button_style = f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 8px; 

                padding: 12px;

                font-weight: bold;

                font-size: 14px;

                min-width: 120px;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """



        self.back_button = QPushButton("Back")

        self.back_button.setStyleSheet(button_style)

        self.back_button.clicked.connect(lambda: self.story_created.emit(None))  # Signal cancel/back



        self.create_button = QPushButton("Create Story")

        self.create_button.setStyleSheet(button_style)

        self.create_button.clicked.connect(self.create_story)



        nav_layout.addStretch(1)

        nav_layout.addWidget(self.back_button)

        nav_layout.addWidget(self.create_button)

        nav_layout.addStretch(1)



        layout.addLayout(nav_layout)



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

            summary = rpg_engine.generate_story_summary(self.game_state, self.model)

            self.summary_ready.emit(summary)

        except Exception as e:

            self.summary_ready.emit(f"Error generating summary: {str(e)}")

        finally:

            self.finished.emit()


class GameStateUpdateWorker(QObject):
    """Worker for updating the game state in a separate thread"""

    update_complete = pyqtSignal(dict, list)  # Emits updated game state and important updates

    def __init__(self, game_state, player_input, dm_response, model):
        super().__init__()
        self.game_state = game_state
        self.player_input = player_input
        self.dm_response = dm_response
        self.model = model

    def update_game_state(self):
        """Update the game state in a background thread"""
        try:
            # Add to conversation history
            current_session = self.game_state['game_info']['session_count']

            # Find current session or create new one
            session_found = False
            for session in self.game_state['conversation_history']:
                if session['session'] == current_session:
                    session['exchanges'].append({"speaker": "Player", "text": self.player_input})
                    session['exchanges'].append({"speaker": "DM", "text": self.dm_response})
                    session_found = True
                    break

            if not session_found:
                self.game_state['conversation_history'].append({
                    "session": current_session,
                    "exchanges": [
                        {"speaker": "Player", "text": self.player_input},
                        {"speaker": "DM", "text": self.dm_response}
                    ]
                })

            # Get plot pacing preference
            plot_pace = self.game_state['game_info'].get('plot_pace', 'Balanced')

            # Update memory
            memory_updates, important_updates = rpg_engine.extract_memory_updates(
                self.player_input,
                self.dm_response,
                self.game_state['narrative_memory'],
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

            # Dynamic element creation from the rpg_engine.py functions
            self.game_state = rpg_engine.update_dynamic_elements(self.game_state, memory_updates)

            # Store important updates
            if important_updates:
                self.game_state['important_updates'] = important_updates

            # Save the game state
            story_name = self.game_state['game_info']['title']
            rpg_engine.save_game_state(self.game_state, story_name)

            # Emit the signal with the updated game state
            self.update_complete.emit(self.game_state, important_updates)

        except Exception as e:
            print(f"Error updating game state: {e}")
            # Still emit the signal with the original game state if there's an error
            self.update_complete.emit(self.game_state, [])

class RepetitionDetector:
    """Class to detect and measure repetition in AI responses"""

    def __init__(self, threshold=0.7, memory_size=5):
        """
        Initialize the repetition detector

        Args:
            threshold: Similarity threshold above which responses are considered repetitive
            memory_size: Number of previous responses to keep in memory for comparison
        """
        self.recent_responses = []
        self.threshold = threshold
        self.memory_size = memory_size

    def similarity_score(self, text1, text2):
        """Calculate similarity between two texts using simple n-gram approach"""
        # Convert to lowercase and tokenize
        words1 = text1.lower().split()
        words2 = text2.lower().split()

        # Create n-grams (using trigrams)
        def get_ngrams(words, n=3):
            return [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]

        # Get n-grams, handle cases with fewer than n words
        if len(words1) < 3 or len(words2) < 3:
            # Fall back to single words for very short texts
            ngrams1 = set(words1)
            ngrams2 = set(words2)
        else:
            ngrams1 = set(get_ngrams(words1))
            ngrams2 = set(get_ngrams(words2))

        if not ngrams1 or not ngrams2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))

        return intersection / union if union > 0 else 0.0

    def is_repetitive(self, new_response):
        """Check if the new response is too similar to recent responses"""
        for old_response in self.recent_responses:
            if self.similarity_score(old_response, new_response) > self.threshold:
                return True
        return False

    def add_response(self, response):
        """Add a response to memory, maintaining the memory size"""
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.memory_size:
            self.recent_responses.pop(0)

    def get_repetition_score(self, new_response):
        """Get the highest similarity score with any recent response"""
        if not self.recent_responses:
            return 0.0

        scores = [self.similarity_score(old, new_response) for old in self.recent_responses]
        return max(scores) if scores else 0.0


class LaceAIdventureGUI(QMainWindow):

    """Main window for the adventure game"""



    def __init__(self):

        super().__init__()

        self.game_state = None

        self.story_name = None

        self.model = None

        self.setup_ui()



    def setup_ui(self):

        """Set up the main UI components with AI settings tab"""

        self.setWindowTitle("Lace's AIdventure Game")

        self.setMinimumSize(1000, 750)  # Increased minimum size for better layout



        # Set application style

        self.setStyleSheet(f"""

            QMainWindow, QWidget, QDialog {{ background-color: {BG_COLOR}; }}

            QLabel {{ color: #4A2D7D; font-weight: 450; }}



            /* Tab styling for better readability */

            QTabBar::tab {{

                background-color: #E1D4F2;       /* Light purple background */

                color: #3A1E64;                  /* Dark purple text */

                border: 1px solid {DM_NAME_COLOR};

                border-bottom: none;

                border-top-left-radius: 4px;

                border-top-right-radius: 4px;

                padding: 8px 15px;

                margin-right: 2px;

                font-weight: bold;

            }}



            QTabBar::tab:selected {{

                background-color: {DM_NAME_COLOR};

                color: white;                    /* White text on purple background */

                border: 1px solid {HIGHLIGHT_COLOR};

                border-bottom: none;

            }}



            QTabBar::tab:hover:!selected {{

                background-color: #C9B6E4;       /* Medium purple for hover */

            }}



            /* Improved dropdown styling */

            QComboBox {{

                background-color: white;

                selection-background-color: {DM_NAME_COLOR};

                selection-color: white;

                color: #3A1E64;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 4px;

                padding: 5px;

                min-height: 25px;

            }}



            QComboBox::drop-down {{

                subcontrol-origin: padding;

                subcontrol-position: top right;

                width: 25px;

                border-left: 1px solid {DM_NAME_COLOR};

                background-color: {DM_NAME_COLOR};

            }}



            QComboBox::down-arrow {{

                width: 12px;

                height: 12px;

            }}



            QComboBox QAbstractItemView {{

                background-color: white;

                color: #3A1E64;

                selection-background-color: {DM_NAME_COLOR};

                selection-color: white;

                border: 1px solid {DM_NAME_COLOR};

            }}



            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 8px;

                margin: 4px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

            QPushButton:disabled {{

                background-color: #B0A8C0;

                color: #E6E6E6;

            }}



            QGroupBox {{ 

                border: 1px solid {DM_NAME_COLOR}; 

                border-radius: 8px; 

                margin-top: 12px; 

                padding: 8px;

            }}

            QGroupBox::title {{ 

                color: {HIGHLIGHT_COLOR}; 

                subcontrol-origin: margin;

                left: 10px;

                padding: 0 5px 0 5px;

                font-weight: bold;

            }}



            QTabWidget::pane {{ 

                border: 1px solid {DM_NAME_COLOR}; 

                border-radius: 8px; 

                padding: 5px;

            }}



            QLineEdit, QTextEdit {{ 

                border: 1px solid {DM_NAME_COLOR}; 

                color: #3A1E64;  /* Dark text for inputs */

                border-radius: 4px; 

                padding: 6px; 

                background-color: white;

                selection-background-color: {DM_NAME_COLOR};

                selection-color: white;

            }}



            QScrollArea {{ 

                border: none; 

                background-color: {BG_COLOR};

            }}



            QListWidget, QListView {{ 

                color: #3A1E64;  /* Darker text for lists */

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 5px;

                padding: 5px;

            }}



            QListWidget::item, QListView::item {{ 

                padding: 5px; 

                color: #3A1E64;

            }}



            QListWidget::item:selected, QListView::item:selected {{ 

                background-color: {DM_NAME_COLOR}; 

                color: white; 

            }}



            /* Slider styling */

            QSlider::groove:horizontal {{

                border: 1px solid {DM_NAME_COLOR};

                height: 8px;

                background: white;

                margin: 2px 0;

                border-radius: 4px;

            }}



            QSlider::handle:horizontal {{

                background: {ACCENT_COLOR};

                border: 1px solid {HIGHLIGHT_COLOR};

                width: 18px;

                margin: -2px 0;

                border-radius: 9px;

            }}



            QSlider::handle:horizontal:hover {{

                background: {HIGHLIGHT_COLOR};

            }}



            QSlider::add-page:horizontal {{

                background: white;

                border-radius: 4px;

            }}



            QSlider::sub-page:horizontal {{

                background: #C9B6E4;

                border-radius: 4px;

            }}



            /* Scroll area and scrollbar styling */

            QScrollBar:vertical {{

                border: none;

                background: #E1D4F2;

                width: 10px;

                margin: 0px;

            }}



            QScrollBar::handle:vertical {{

                background: {DM_NAME_COLOR};

                border-radius: 5px;

                min-height: 20px;

            }}



            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{

                border: none;

                background: none;

            }}

        """)



        # Create the central widget and layout

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(12, 12, 12, 12)

        main_layout.setSpacing(10)



        # Create the title - with seamless background and button-colored text

        title_label = QLabel("Lace's AIdventure Game")

        title_font = QFont()

        title_font.setPointSize(28)  # Slightly larger

        title_font.setBold(True)

        title_label.setFont(title_font)

        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label.setStyleSheet(f"color: {ACCENT_COLOR}; margin-bottom: 15px;")

        title_label.setMinimumHeight(60)  # Ensure enough vertical space



        # Add the title to the main layout

        main_layout.addWidget(title_label)



        # Create tab widget for different screens

        self.tabs = QTabWidget()

        self.tabs.setTabPosition(QTabWidget.TabPosition.North)



        # Create the game tabs

        self.main_menu_tab = self.create_main_menu_tab()

        self.game_tab = self.create_game_tab()

        self.story_creation_tab = self.create_story_creation_tab()

        self.story_management_tab = self.create_story_management_tab()

        self.ai_settings_tab = self.create_ai_settings_tab()  # New AI settings tab



        # Add the tabs to the tab widget

        self.tabs.addTab(self.main_menu_tab, "Main Menu")

        self.tabs.addTab(self.game_tab, "Game")

        self.tabs.addTab(self.story_creation_tab, "Create Story")

        self.tabs.addTab(self.story_management_tab, "Manage Stories")

        self.tabs.addTab(self.ai_settings_tab, "AI Settings")  # Add the new tab



        # Add the tab widget to the main layout

        main_layout.addWidget(self.tabs)



        # Start with the main menu and hide other tabs

        self.tabs.setCurrentIndex(0)

        self.tabs.setTabVisible(1, False)  # Hide game tab initially

        self.tabs.setTabVisible(2, False)  # Hide story creation tab initially

        self.tabs.setTabVisible(3, False)  # Hide story management tab initially

        self.tabs.setTabVisible(4, False)  # Hide AI settings tab initially



        # Add AI settings button to the game tab

        self.add_ai_settings_to_game_tab()



    def create_main_menu_tab(self):

        """Create the main menu interface with AI settings option"""

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(20, 20, 20, 20)  # Add more padding

        layout.setSpacing(15)  # More space between elements



        # Add a subtitle

        subtitle_label = QLabel("Ethically ran, locally hosted AI text-adventures with no limitations.")

        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_font = QFont()

        subtitle_font.setPointSize(16)

        subtitle_label.setFont(subtitle_font)

        subtitle_label.setStyleSheet(f"color: {DM_NAME_COLOR}; margin-bottom: 20px;")

        layout.addWidget(subtitle_label)



        # Add some spacing

        layout.addSpacing(40)



        # Create a container for the buttons with fixed width

        button_container = QWidget()

        button_container.setFixedWidth(350)  # Wider buttons

        button_layout = QVBoxLayout(button_container)

        button_layout.setSpacing(15)  # More space between buttons



        # Custom button style

        button_style = f"""

            QPushButton {{

                background-color: {DM_NAME_COLOR}; 

                color: white; 

                border-radius: 8px; 

                padding: 12px;

                font-size: 16px;

                font-weight: bold;

            }}

            QPushButton:hover {{

                background-color: {HIGHLIGHT_COLOR};

            }}

        """



        # Add buttons for main menu options

        new_story_button = QPushButton("Create New Story")

        new_story_button.setMinimumHeight(60)

        new_story_button.setStyleSheet(button_style)



        load_story_button = QPushButton("Load Existing Story")

        load_story_button.setMinimumHeight(60)

        load_story_button.setStyleSheet(button_style)



        manage_stories_button = QPushButton("Manage Stories")

        manage_stories_button.setMinimumHeight(60)

        manage_stories_button.setStyleSheet(button_style)



        ai_settings_button = QPushButton("AI Settings")  # New AI settings button

        ai_settings_button.setMinimumHeight(60)

        ai_settings_button.setStyleSheet(button_style)



        exit_button = QPushButton("Exit")

        exit_button.setMinimumHeight(60)

        exit_button.setStyleSheet(button_style)



        # Connect signals to slots

        new_story_button.clicked.connect(self.show_story_creation)

        load_story_button.clicked.connect(self.show_story_load)

        manage_stories_button.clicked.connect(self.show_story_management)

        ai_settings_button.clicked.connect(self.show_ai_settings)  # New slot

        exit_button.clicked.connect(self.close)



        # Add buttons to layout

        button_layout.addWidget(new_story_button)

        button_layout.addWidget(load_story_button)

        button_layout.addWidget(manage_stories_button)

        button_layout.addWidget(ai_settings_button)  # Add AI settings button

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

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(10)



        # Create a splitter for resizable panels

        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.setHandleWidth(8)  # Wider handle for easier resizing

        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {DM_NAME_COLOR}; }}")



        # Create the game display panel

        game_panel = QWidget()

        game_panel.setStyleSheet(f"background-color: #FFFFFF; border-radius: 10px;")

        game_layout = QVBoxLayout(game_panel)

        game_layout.setContentsMargins(12, 12, 12, 12)

        game_layout.setSpacing(10)



        # Create the text display area

        self.text_display = StreamingTextDisplay()

        self.text_display.setStyleSheet(f"""

            QTextEdit {{

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 10px;

                padding: 10px;

                font-size: 14px;

            }}

        """)

        game_layout.addWidget(self.text_display)



        # Create the input area

        input_layout = QHBoxLayout()

        input_layout.setSpacing(8)



        self.input_field = QLineEdit()

        self.input_field.setPlaceholderText("Enter your command...")

        self.input_field.setMinimumHeight(40)

        self.input_field.setStyleSheet(f"""

            QLineEdit {{

                border: 2px solid {DM_NAME_COLOR};

                border-radius: 8px;

                padding: 8px;

                font-size: 14px;

                color: #3A1E64;

            }}

            QLineEdit:focus {{ border-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.input_field.returnPressed.connect(self.process_input)



        self.send_button = QPushButton("Send")

        self.send_button.setMinimumHeight(40)

        self.send_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {DM_NAME_COLOR};

                color: white;

                border-radius: 8px;

                padding: 8px 20px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.send_button.clicked.connect(self.process_input)



        input_layout.addWidget(self.input_field, 7)  # 70% of space

        input_layout.addWidget(self.send_button, 3)  # 30% of space

        game_layout.addLayout(input_layout)



        # Create the command buttons

        cmd_layout = QHBoxLayout()

        cmd_layout.setSpacing(10)



        button_style = f"""

            QPushButton {{

                background-color: {ACCENT_COLOR};

                color: white;

                border-radius: 6px;

                padding: 8px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """



        self.save_button = QPushButton("Save")

        self.save_button.setStyleSheet(button_style)

        self.save_button.clicked.connect(self.save_game)



        self.memory_button = QPushButton("Memory")

        self.memory_button.setStyleSheet(button_style)

        self.memory_button.clicked.connect(self.show_memory)



        self.summary_button = QPushButton("Summary")

        self.summary_button.setStyleSheet(button_style)

        self.summary_button.clicked.connect(self.show_summary)



        self.quit_button = QPushButton("Quit")

        self.quit_button.setStyleSheet(button_style)

        self.quit_button.clicked.connect(self.quit_game)



        cmd_layout.addWidget(self.save_button)

        cmd_layout.addWidget(self.memory_button)

        cmd_layout.addWidget(self.summary_button)

        cmd_layout.addWidget(self.quit_button)



        game_layout.addLayout(cmd_layout)



        # Create the game status panel

        status_panel = QScrollArea()

        status_panel.setWidgetResizable(True)

        status_panel.setMinimumWidth(280)

        status_panel.setMaximumWidth(350)

        status_panel.setStyleSheet(f"""

            QScrollArea {{ 

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 10px;

            }}

        """)



        status_content = QWidget()

        status_content.setStyleSheet(f"background-color: white; padding: 10px;")

        self.status_layout = QVBoxLayout(status_content)

        self.status_layout.setSpacing(15)  # More space between sections



        group_box_style = f"""

            QGroupBox {{ 

                background-color: #F8F4FF;

                border: 1px solid {DM_NAME_COLOR}; 

                border-radius: 8px; 

                margin-top: 12px; 

                padding: 10px;

            }}

            QGroupBox::title {{ 

                color: {HIGHLIGHT_COLOR}; 

                subcontrol-origin: margin;

                left: 10px;

                padding: 0 5px;

                font-weight: bold;

            }}

        """





        # Game info section

        game_info_group = QGroupBox("Game Info")

        game_info_group.setStyleSheet(group_box_style)

        game_info_layout = QVBoxLayout(game_info_group)

        game_info_layout.setSpacing(8)



        self.game_title_label = QLabel("Title: ")

        self.game_world_label = QLabel("World: ")

        self.game_location_label = QLabel("Location: ")



        # Add styling to the labels

        self.game_title_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.game_world_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.game_location_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")



        game_info_layout.addWidget(self.game_title_label)

        game_info_layout.addWidget(self.game_world_label)

        game_info_layout.addWidget(self.game_location_label)



        # Character info section

        character_info_group = QGroupBox("Character")

        character_info_group.setStyleSheet(group_box_style)

        character_info_layout = QVBoxLayout(character_info_group)

        character_info_layout.setSpacing(8)



        self.character_name_label = QLabel("Name: ")

        self.character_class_label = QLabel("Class: ")

        self.character_race_label = QLabel("Race: ")

        self.character_health_label = QLabel("Health: ")



        # Add styling to the labels

        self.character_name_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.character_class_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.character_race_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.character_health_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")



        character_info_layout.addWidget(self.character_name_label)

        character_info_layout.addWidget(self.character_class_label)

        character_info_layout.addWidget(self.character_race_label)

        character_info_layout.addWidget(self.character_health_label)



        # Quest info section

        quest_info_group = QGroupBox("Current Quest")

        quest_info_group.setStyleSheet(group_box_style)

        quest_info_layout = QVBoxLayout(quest_info_group)

        quest_info_layout.setSpacing(8)



        self.quest_name_label = QLabel("Name: ")

        self.quest_desc_label = QLabel("Description: ")

        self.quest_desc_label.setWordWrap(True)



        # Add styling to the labels

        self.quest_name_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")

        self.quest_desc_label.setStyleSheet("color: #4A2D7D; font-weight: bold;")



        quest_info_layout.addWidget(self.quest_name_label)

        quest_info_layout.addWidget(self.quest_desc_label)



        # NPCs section

        npcs_group = QGroupBox("NPCs Present")

        npcs_group.setStyleSheet(group_box_style)

        npcs_layout = QVBoxLayout(npcs_group)

        npcs_layout.setSpacing(5)



        self.npcs_list = QListWidget()

        self.npcs_list.setStyleSheet(f"""

            QListWidget {{ 

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 5px;

                padding: 5px;

                color: #4A2D7D;  /* Darker text for list items */

            }}

            QListWidget::item {{ padding: 5px; }}

            QListWidget::item:selected {{ 

                background-color: {DM_NAME_COLOR}; 

                color: white; 

            }}

        """)

        npcs_layout.addWidget(self.npcs_list)



        # Add all sections to the status layout

        self.status_layout.addWidget(game_info_group)

        self.status_layout.addWidget(character_info_group)

        self.status_layout.addWidget(quest_info_group)

        self.status_layout.addWidget(npcs_group)

        self.status_layout.addStretch()



        status_panel.setWidget(status_content)

        locations_group = QGroupBox("Known Locations")
        locations_group.setStyleSheet(group_box_style)
        locations_layout = QVBoxLayout(locations_group)
        locations_layout.setSpacing(5)

        self.locations_list = QListWidget()
        self.locations_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: white;
                border: 1px solid {DM_NAME_COLOR};
                border-radius: 5px;
                padding: 5px;
                color: #4A2D7D;
            }}
            QListWidget::item {{ padding: 5px; }}
            QListWidget::item:selected {{ 
                background-color: {DM_NAME_COLOR}; 
                color: white; 
            }}
        """)
        self.locations_list.itemClicked.connect(self.show_location_details)
        locations_layout.addWidget(self.locations_list)

        # Quests section
        quests_group = QGroupBox("Active Quests")
        quests_group.setStyleSheet(group_box_style)
        quests_layout = QVBoxLayout(quests_group)
        quests_layout.setSpacing(5)

        self.quests_list = QListWidget()
        self.quests_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: white;
                border: 1px solid {DM_NAME_COLOR};
                border-radius: 5px;
                padding: 5px;
                color: #4A2D7D;
            }}
            QListWidget::item {{ padding: 5px; }}
            QListWidget::item:selected {{ 
                background-color: {DM_NAME_COLOR}; 
                color: white; 
            }}
        """)
        self.quests_list.itemClicked.connect(self.show_quest_details)
        quests_layout.addWidget(self.quests_list)

        # Add all sections to the status layout
        self.status_layout.addWidget(game_info_group)
        self.status_layout.addWidget(character_info_group)
        self.status_layout.addWidget(quest_info_group)
        self.status_layout.addWidget(npcs_group)
        self.status_layout.addWidget(locations_group)
        self.status_layout.addWidget(quests_group)
        self.status_layout.addStretch()



        # Add the panels to the splitter

        splitter.addWidget(game_panel)

        splitter.addWidget(status_panel)



        # Set the initial sizes

        splitter.setSizes([600, 300])



        # Add the splitter to the layout

        layout.addWidget(splitter)



        return tab



    def create_story_creation_tab(self):

        """Create the story creation interface with improved layout"""

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(15)



        # Create the story creation wizard

        self.story_wizard = StoryCreationWizard()

        self.story_wizard.story_created.connect(self.create_new_story)



        layout.addWidget(self.story_wizard)



        return tab



    def create_story_management_tab(self):

        """Create the story management interface"""

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(15)



        # Add title

        title_label = QLabel("Manage Stories")

        title_font = QFont()

        title_font.setPointSize(18)

        title_font.setBold(True)

        title_label.setFont(title_font)

        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; margin-bottom: 15px;")

        layout.addWidget(title_label)



        # Create a list widget for the stories

        self.stories_list = QListWidget()

        self.stories_list.setStyleSheet(f"""

            QListWidget {{ 

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 8px;

                padding: 10px;

                font-size: 14px;

                color: #3A1E64;

            }}

            QListWidget::item {{ 

                padding: 8px; 

                border-bottom: 1px solid #E1D4F2;

            }}

            QListWidget::item:selected {{ 

                background-color: {DM_NAME_COLOR}; 

                color: white; 

            }}

        """)

        layout.addWidget(self.stories_list)



        # Create buttons for actions

        button_layout = QHBoxLayout()

        button_layout.setSpacing(15)



        self.load_story_button = QPushButton("Load Selected Story")

        self.load_story_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.load_story_button.clicked.connect(self.load_selected_story)



        self.delete_story_button = QPushButton("Delete Selected Story")

        self.delete_story_button.setStyleSheet(f"""

            QPushButton {{

                background-color: #D32F2F; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: #B71C1C; }}

        """)

        self.delete_story_button.clicked.connect(self.delete_selected_story)



        self.refresh_button = QPushButton("Refresh List")

        self.refresh_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.refresh_button.clicked.connect(self.refresh_stories_list)



        button_layout.addWidget(self.load_story_button)

        button_layout.addWidget(self.delete_story_button)

        button_layout.addWidget(self.refresh_button)



        layout.addLayout(button_layout)



        # Back button

        back_button = QPushButton("Back to Main Menu")

        back_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

                margin-top: 10px;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0))

        layout.addWidget(back_button)



        return tab



    def create_ai_settings_tab(self):

        """Create the AI settings interface"""

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(15)



        # Add title

        title_label = QLabel("AI Model Settings")

        title_font = QFont()

        title_font.setPointSize(18)

        title_font.setBold(True)

        title_label.setFont(title_font)

        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; margin-bottom: 15px;")

        layout.addWidget(title_label)



        # Create form layout for settings

        settings_form = QWidget()

        form_layout = QFormLayout(settings_form)

        form_layout.setVerticalSpacing(15)

        form_layout.setHorizontalSpacing(20)

        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)



        # Current story selection

        story_label = QLabel("Current Story:")

        story_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.ai_settings_story_label = QLabel("No story selected")

        form_layout.addRow(story_label, self.ai_settings_story_label)



        # Model selection

        model_label = QLabel("AI Model:")

        model_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        self.ai_settings_model_combo = QComboBox()

        # Populate with available models

        available_models = rpg_engine.get_available_ollama_models()

        self.ai_settings_model_combo.addItems(available_models)

        form_layout.addRow(model_label, self.ai_settings_model_combo)



        # Temperature setting

        temp_label = QLabel("Temperature:")

        temp_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        temp_layout = QHBoxLayout()



        self.ai_settings_temp_slider = QSlider(Qt.Orientation.Horizontal)

        self.ai_settings_temp_slider.setMinimum(1)  # 0.1

        self.ai_settings_temp_slider.setMaximum(20)  # 2.0

        self.ai_settings_temp_slider.setValue(7)  # Default 0.7

        self.ai_settings_temp_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.ai_settings_temp_slider.setTickInterval(1)



        self.ai_settings_temp_value = QLabel("0.7")

        self.ai_settings_temp_value.setMinimumWidth(30)

        self.ai_settings_temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)



        self.ai_settings_temp_slider.valueChanged.connect(

            lambda value: self.ai_settings_temp_value.setText(f"{value / 10:.1f}")

        )



        temp_layout.addWidget(self.ai_settings_temp_slider)

        temp_layout.addWidget(self.ai_settings_temp_value)



        form_layout.addRow(temp_label, temp_layout)



        # Top P setting

        top_p_label = QLabel("Top P:")

        top_p_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")

        top_p_layout = QHBoxLayout()



        self.ai_settings_top_p_slider = QSlider(Qt.Orientation.Horizontal)

        self.ai_settings_top_p_slider.setMinimum(1)  # 0.1

        self.ai_settings_top_p_slider.setMaximum(10)  # 1.0

        self.ai_settings_top_p_slider.setValue(9)  # Default 0.9

        self.ai_settings_top_p_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.ai_settings_top_p_slider.setTickInterval(1)



        self.ai_settings_top_p_value = QLabel("0.9")

        self.ai_settings_top_p_value.setMinimumWidth(30)

        self.ai_settings_top_p_value.setAlignment(Qt.AlignmentFlag.AlignCenter)



        self.ai_settings_top_p_slider.valueChanged.connect(

            lambda value: self.ai_settings_top_p_value.setText(f"{value / 10:.1f}")

        )



        top_p_layout.addWidget(self.ai_settings_top_p_slider)

        top_p_layout.addWidget(self.ai_settings_top_p_value)



        form_layout.addRow(top_p_label, top_p_layout)

        # Max Tokens setting
        max_tokens_label = QLabel("Max Tokens:")
        max_tokens_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        max_tokens_layout = QHBoxLayout()

        self.ai_settings_max_tokens_slider = QSlider(Qt.Orientation.Horizontal)
        self.ai_settings_max_tokens_slider.setMinimum(500)  # Minimum reasonable value
        self.ai_settings_max_tokens_slider.setMaximum(4096)  # Maximum for most models
        self.ai_settings_max_tokens_slider.setSingleStep(100)
        self.ai_settings_max_tokens_slider.setTickInterval(500)
        self.ai_settings_max_tokens_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ai_settings_max_tokens_slider.setValue(2048)  # Default value

        self.ai_settings_max_tokens_value = QLabel("2048")
        self.ai_settings_max_tokens_value.setMinimumWidth(50)
        self.ai_settings_max_tokens_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ai_settings_max_tokens_slider.valueChanged.connect(
            lambda value: self.ai_settings_max_tokens_value.setText(str(value))
        )

        max_tokens_layout.addWidget(self.ai_settings_max_tokens_slider)
        max_tokens_layout.addWidget(self.ai_settings_max_tokens_value)

        form_layout.addRow(max_tokens_label, max_tokens_layout)

        # Add labels for token slider
        tokens_labels = QHBoxLayout()
        tokens_labels.addWidget(QLabel("500"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("1500"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("2500"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("3500"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("4096"))
        form_layout.addRow("", tokens_labels)

        # Response length setting
        response_length_label = QLabel("Response Length:")
        response_length_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        response_length_layout = QHBoxLayout()

        self.ai_settings_response_length_slider = QSlider(Qt.Orientation.Horizontal)
        self.ai_settings_response_length_slider.setMinimum(1)  # Very Short
        self.ai_settings_response_length_slider.setMaximum(5)  # Very Detailed
        self.ai_settings_response_length_slider.setValue(3)  # Default Medium
        self.ai_settings_response_length_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ai_settings_response_length_slider.setTickInterval(1)

        # Labels for the slider positions
        response_length_labels = QHBoxLayout()
        response_length_labels.addWidget(QLabel("Brief"))
        response_length_labels.addStretch(1)
        response_length_labels.addWidget(QLabel("Medium"))
        response_length_labels.addStretch(1)
        response_length_labels.addWidget(QLabel("Detailed"))

        # Current setting label
        self.ai_settings_response_length_value = QLabel("Medium")
        self.ai_settings_response_length_value.setMinimumWidth(80)
        self.ai_settings_response_length_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Connect the slider to update the label
        self.ai_settings_response_length_slider.valueChanged.connect(self.update_response_length_label)

        response_length_layout.addWidget(self.ai_settings_response_length_slider)
        response_length_layout.addWidget(self.ai_settings_response_length_value)

        form_layout.addRow(response_length_label, response_length_layout)
        form_layout.addRow("", response_length_labels)



        # Add settings form to layout

        layout.addWidget(settings_form)



        # Add explanation of settings

        explanation_text = QTextEdit()

        explanation_text.setReadOnly(True)

        explanation_text.setMaximumHeight(150)

        explanation_text.setStyleSheet(f"""

            QTextEdit {{

                background-color: white;

                border: 1px solid {DM_NAME_COLOR};

                border-radius: 8px;

                padding: 15px;

                color: #3A1E64;

            }}

        """)

        explanation_text.setHtml(f"""
            <h3 style='color: {HIGHLIGHT_COLOR};'>About These Settings</h3>
            <p><b>Temperature:</b> Controls randomness. Lower values (0.1-0.4) make responses more focused and deterministic. 
            Higher values (0.7-1.0) make responses more creative and varied.</p>
            <p><b>Top P:</b> Controls diversity by considering only the most likely tokens. Lower values make text more focused, 
            higher values allow more variety.</p>
            <p><b>Response Length:</b> Controls how verbose or concise responses should be, from very brief (1-2 sentences) 
            to very detailed (11+ sentences). This is a stylistic preference.</p>
            <p><b>Max Tokens:</b> Hard limit on response length. If set too low, responses may be cut off mid-sentence. 
            Higher values allow longer responses but may slow down generation.</p>
            <p><b>Note:</b> Response Length and Max Tokens work together. The AI will respect your verbosity 
            preference until it reaches the token limit.</p>
        """)



        layout.addWidget(explanation_text)



        # Add action buttons

        button_layout = QHBoxLayout()

        button_layout.setSpacing(15)



        button_style = f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 10px;

                font-weight: bold;

                min-width: 120px;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

            QPushButton:disabled {{ background-color: #AAA; color: #EEE; }}

        """



        self.ai_settings_apply_button = QPushButton("Apply Changes")

        self.ai_settings_apply_button.setStyleSheet(button_style)

        self.ai_settings_apply_button.clicked.connect(self.apply_ai_settings)



        self.ai_settings_reset_button = QPushButton("Reset to Defaults")

        self.ai_settings_reset_button.setStyleSheet(button_style)

        self.ai_settings_reset_button.clicked.connect(self.reset_ai_settings)



        button_layout.addStretch(1)

        button_layout.addWidget(self.ai_settings_reset_button)

        button_layout.addWidget(self.ai_settings_apply_button)

        button_layout.addStretch(1)



        layout.addLayout(button_layout)



        # Add back button

        back_button = QPushButton("Back to Main Menu")

        back_button.setStyleSheet(button_style)

        back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0))



        back_layout = QHBoxLayout()

        back_layout.addStretch(1)

        back_layout.addWidget(back_button)

        back_layout.addStretch(1)



        layout.addLayout(back_layout)

        layout.addStretch()



        # Initialize button state

        self.update_ai_settings_state()



        return tab

    def update_ai_settings_state(self):
        """Update the state of the AI settings controls based on current game state"""
        if self.game_state:
            # Enable controls and update values
            self.ai_settings_story_label.setText(self.game_state['game_info']['title'])
            model_name = self.game_state['game_info'].get('model_name', 'mistral-small')

            # Find model in combo box
            index = self.ai_settings_model_combo.findText(model_name)
            if index >= 0:
                self.ai_settings_model_combo.setCurrentIndex(index)

            # Set temperature
            temperature = self.game_state['game_info'].get('temperature', 0.7)
            self.ai_settings_temp_slider.setValue(int(temperature * 10))
            self.ai_settings_temp_value.setText(f"{temperature:.1f}")

            # Set top_p
            top_p = self.game_state['game_info'].get('top_p', 0.9)
            self.ai_settings_top_p_slider.setValue(int(top_p * 10))
            self.ai_settings_top_p_value.setText(f"{top_p:.1f}")

            # Set max tokens with slider instead of spin box
            max_tokens = self.game_state['game_info'].get('max_tokens', 2048)
            self.ai_settings_max_tokens_slider.setValue(max_tokens)
            self.ai_settings_max_tokens_value.setText(str(max_tokens))

            # Set response length slider
            response_length = self.game_state['game_info'].get('response_length', 3)
            self.ai_settings_response_length_slider.setValue(response_length)
            self.update_response_length_label(response_length)

            # Enable buttons
            self.ai_settings_apply_button.setEnabled(True)
            self.ai_settings_reset_button.setEnabled(True)
        else:
            # Disable controls
            self.ai_settings_story_label.setText("No story selected")
            self.ai_settings_temp_slider.setValue(7)  # Default 0.7
            self.ai_settings_top_p_slider.setValue(9)  # Default 0.9
            self.ai_settings_max_tokens_slider.setValue(2048)  # Default 2048
            self.ai_settings_max_tokens_value.setText("2048")
            self.ai_settings_response_length_slider.setValue(3)  # Default Medium
            self.update_response_length_label(3)

            # Disable buttons
            self.ai_settings_apply_button.setEnabled(False)
            self.ai_settings_reset_button.setEnabled(False)

    def update_response_length_label(self, value):
        """Update the response length label based on slider value"""
        length_labels = {
            1: "Very Brief",
            2: "Brief",
            3: "Medium",
            4: "Detailed",
            5: "Very Detailed"
        }
        self.ai_settings_response_length_value.setText(length_labels[value])

    def apply_ai_settings(self):
        """Apply the current AI settings to the active game"""
        # Check if a generation is in progress
        if hasattr(self, 'generation_thread') and self.generation_thread.isRunning():
            QMessageBox.warning(self, "Settings Locked",
                                "Cannot change AI settings while text generation or memory writing is in progress. Please wait until the current response is complete.")
            return
        if not self.game_state:
            return

        # Get values from controls
        model_name = self.ai_settings_model_combo.currentText()
        temperature = self.ai_settings_temp_slider.value() / 10.0
        top_p = self.ai_settings_top_p_slider.value() / 10.0
        max_tokens = self.ai_settings_max_tokens_slider.value()  # Updated to use slider
        response_length = self.ai_settings_response_length_slider.value()

        # Check if model has changed
        model_changed = model_name != self.game_state['game_info'].get('model_name', 'mistral-small')

        # Store values in game state
        self.game_state['game_info']['model_name'] = model_name
        self.game_state['game_info']['temperature'] = temperature
        self.game_state['game_info']['top_p'] = top_p
        self.game_state['game_info']['max_tokens'] = max_tokens
        self.game_state['game_info']['response_length'] = response_length

        # Save the game state
        rpg_engine.save_game_state(self.game_state, self.story_name)

        # Update the model
        if self.model:
            if model_changed:
                # Create a new model instance if the model name changed
                self.model.change_model(model_name)

            # Update settings
            self.model.update_settings(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )

        # Show confirmation
        response_length_text = self.ai_settings_response_length_value.text()
        QMessageBox.information(self, "Settings Applied",
                                f"AI settings have been updated.\nModel: {model_name}\nTemperature: {temperature:.1f}\nResponse Length: {response_length_text}\nMax Tokens: {max_tokens}")

        # Update game display to show notification
        if model_changed:
            self.text_display.append_system_message(f"AI model changed to {model_name}")
        self.text_display.append_system_message(
            f"AI settings updated: Temperature={temperature:.1f}, Response Length={response_length_text}, Max Tokens={max_tokens}")

    def reset_ai_settings(self):
        """Reset AI settings to default values"""
        # Set default values
        self.ai_settings_temp_slider.setValue(7)  # 0.7
        self.ai_settings_top_p_slider.setValue(9)  # 0.9
        self.ai_settings_max_tokens_slider.setValue(2048)  # Default 2048
        self.ai_settings_max_tokens_value.setText("2048")
        self.ai_settings_response_length_slider.setValue(3)  # Medium

        # Find default model
        default_models = ['mistral-small', 'llama3', 'gemma', 'phi-2']
        for model in default_models:
            index = self.ai_settings_model_combo.findText(model)
            if index >= 0:
                self.ai_settings_model_combo.setCurrentIndex(index)
                break



    def add_ai_settings_to_game_tab(self):

        """Add AI settings controls to the game tab for quick access"""

        # Create a settings button in the game interface

        self.game_settings_button = QPushButton("AI Settings")

        self.game_settings_button.setStyleSheet(f"""

            QPushButton {{

                background-color: {ACCENT_COLOR}; 

                color: white; 

                border-radius: 6px; 

                padding: 8px;

                font-weight: bold;

            }}

            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

        """)

        self.game_settings_button.clicked.connect(self.show_game_ai_settings)



        # Add the button to the command layout (usually where Save, Memory, etc. buttons are)

        # Find the existing button layout in your game_tab

        cmd_layout = None

        for child in self.game_tab.findChildren(QHBoxLayout):

            # Try to find the layout that contains the Save button

            for i in range(child.count()):

                item = child.itemAt(i).widget()

                if isinstance(item, QPushButton) and item.text() == "Save":

                    cmd_layout = child

                    break

            if cmd_layout:

                break



        # If we found the command layout, insert our button

        if cmd_layout:

            cmd_layout.insertWidget(2, self.game_settings_button)  # Insert after Memory button

    def show_game_ai_settings(self):
        """Show a compact AI settings dialog during gameplay with the same controls as the main settings tab"""
        # Check if a generation is in progress
        if hasattr(self, 'generation_thread') and self.generation_thread.isRunning():
            QMessageBox.warning(self, "Settings Locked",
                                "Cannot change AI settings while text generation is in progress. Please wait until the current response is complete.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("AI Settings")
        dialog.setMinimumSize(500, 500)  # Increased size to fit all controls
        dialog.setStyleSheet(f"background-color: {BG_COLOR};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create scrollable area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(15)

        # Create form layout for settings
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Model selection
        model_label = QLabel("AI Model:")
        model_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        model_combo = QComboBox()
        available_models = rpg_engine.get_available_ollama_models()
        model_combo.addItems(available_models)

        # Set current model
        current_model = self.game_state['game_info'].get('model_name', 'mistral-small')
        index = model_combo.findText(current_model)
        if index >= 0:
            model_combo.setCurrentIndex(index)

        form_layout.addRow(model_label, model_combo)

        # Temperature setting
        temp_label = QLabel("Temperature:")
        temp_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        temp_layout = QHBoxLayout()

        temp_slider = QSlider(Qt.Orientation.Horizontal)
        temp_slider.setMinimum(1)  # 0.1
        temp_slider.setMaximum(20)  # 2.0
        temp_slider.setValue(int(self.game_state['game_info'].get('temperature', 0.7) * 10))
        temp_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        temp_slider.setTickInterval(1)

        temp_value = QLabel(f"{self.game_state['game_info'].get('temperature', 0.7):.1f}")
        temp_value.setMinimumWidth(30)
        temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        temp_slider.valueChanged.connect(lambda value: temp_value.setText(f"{value / 10:.1f}"))

        temp_layout.addWidget(temp_slider)
        temp_layout.addWidget(temp_value)

        form_layout.addRow(temp_label, temp_layout)

        # Top P setting
        top_p_label = QLabel("Top P:")
        top_p_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        top_p_layout = QHBoxLayout()

        top_p_slider = QSlider(Qt.Orientation.Horizontal)
        top_p_slider.setMinimum(1)  # 0.1
        top_p_slider.setMaximum(10)  # 1.0
        top_p_slider.setValue(int(self.game_state['game_info'].get('top_p', 0.9) * 10))
        top_p_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        top_p_slider.setTickInterval(1)

        top_p_value = QLabel(f"{self.game_state['game_info'].get('top_p', 0.9):.1f}")
        top_p_value.setMinimumWidth(30)
        top_p_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_p_slider.valueChanged.connect(lambda value: top_p_value.setText(f"{value / 10:.1f}"))

        top_p_layout.addWidget(top_p_slider)
        top_p_layout.addWidget(top_p_value)

        form_layout.addRow(top_p_label, top_p_layout)

        # Response Length setting
        response_length_label = QLabel("Response Length:")
        response_length_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        response_length_layout = QHBoxLayout()

        response_length_slider = QSlider(Qt.Orientation.Horizontal)
        response_length_slider.setMinimum(1)  # Very Short
        response_length_slider.setMaximum(5)  # Very Detailed
        response_length_slider.setValue(self.game_state['game_info'].get('response_length', 3))
        response_length_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        response_length_slider.setTickInterval(1)

        # Current setting label
        length_labels = {
            1: "Very Brief",
            2: "Brief",
            3: "Medium",
            4: "Detailed",
            5: "Very Detailed"
        }
        current_length = self.game_state['game_info'].get('response_length', 3)
        response_length_value = QLabel(length_labels.get(current_length, "Medium"))
        response_length_value.setMinimumWidth(80)
        response_length_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Connect the slider to update the label
        response_length_slider.valueChanged.connect(
            lambda value: response_length_value.setText(length_labels.get(value, "Medium"))
        )

        response_length_layout.addWidget(response_length_slider)
        response_length_layout.addWidget(response_length_value)

        form_layout.addRow(response_length_label, response_length_layout)

        # Labels for the response length slider
        response_length_labels = QHBoxLayout()
        very_brief_label = QLabel("Very Brief")
        very_brief_label.setToolTip("1-2 sentences, action-focused only")
        brief_label = QLabel("Brief")
        brief_label.setToolTip("Up to 3 sentences")
        medium_label = QLabel("Medium")
        medium_label.setToolTip("4-6 sentences with balanced description")
        detailed_label = QLabel("Detailed")
        detailed_label.setToolTip("7-10 sentences with rich descriptions")
        very_detailed_label = QLabel("Very Detailed")
        very_detailed_label.setToolTip("11+ sentences with immersive detail")

        response_length_labels.addWidget(very_brief_label)
        response_length_labels.addStretch(1)
        response_length_labels.addWidget(medium_label)
        response_length_labels.addStretch(1)
        response_length_labels.addWidget(very_detailed_label)

        form_layout.addRow("", response_length_labels)

        # Max Tokens setting
        max_tokens_label = QLabel("Max Tokens:")
        max_tokens_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; font-weight: bold;")
        max_tokens_layout = QHBoxLayout()

        max_tokens_slider = QSlider(Qt.Orientation.Horizontal)
        max_tokens_slider.setMinimum(500)  # Minimum reasonable value
        max_tokens_slider.setMaximum(4096)  # Maximum for most models
        max_tokens_slider.setSingleStep(100)
        max_tokens_slider.setTickInterval(500)
        max_tokens_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        max_tokens_slider.setValue(self.game_state['game_info'].get('max_tokens', 2048))  # Get current value

        max_tokens_value = QLabel(str(self.game_state['game_info'].get('max_tokens', 2048)))
        max_tokens_value.setMinimumWidth(50)
        max_tokens_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        max_tokens_slider.valueChanged.connect(
            lambda value: max_tokens_value.setText(str(value))
        )

        max_tokens_layout.addWidget(max_tokens_slider)
        max_tokens_layout.addWidget(max_tokens_value)

        form_layout.addRow(max_tokens_label, max_tokens_layout)

        # Labels for tokens slider (simplified)
        tokens_labels = QHBoxLayout()
        tokens_labels.addWidget(QLabel("500"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("2000"))
        tokens_labels.addStretch(3)
        tokens_labels.addWidget(QLabel("4096"))
        form_layout.addRow("", tokens_labels)

        # Add explanation text
        explanation = QTextEdit()
        explanation.setReadOnly(True)
        explanation.setMaximumHeight(150)
        explanation.setStyleSheet(f"""
            QTextEdit {{
                background-color: white;
                border: 1px solid {DM_NAME_COLOR};
                border-radius: 8px;
                padding: 10px;
                color: #3A1E64;
            }}
        """)
        explanation.setHtml(f"""
            <h3 style='color: {HIGHLIGHT_COLOR};'>Settings Quick Guide</h3>
            <p><b>Response Length:</b> Controls verbosity from brief (1-2 sentences) to detailed (11+ sentences).</p>
            <p><b>Max Tokens:</b> Hard limit on response size. Higher allows longer responses but may slow generation.</p>
            <p><b>Temperature:</b> Controls randomness. Higher values (0.7-1.0) increase creativity.</p>
        """)

        scroll_layout.addLayout(form_layout)
        scroll_layout.addWidget(explanation)
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #888; 
                color: white; 
                border-radius: 6px; 
                padding: 10px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{ background-color: #666; }}
        """)
        cancel_button.clicked.connect(dialog.reject)

        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR}; 
                color: white; 
                border-radius: 6px; 
                padding: 10px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}
        """)

        # Connect apply button to apply all settings safely
        apply_button.clicked.connect(
            lambda: self.apply_in_game_settings_safely(
                dialog,
                model_combo.currentText(),
                temp_slider.value() / 10.0,
                top_p_slider.value() / 10.0,
                response_length_slider.value(),
                max_tokens_slider.value()
            )
        )

        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)
        button_layout.addStretch(1)

        layout.addLayout(button_layout)

        dialog.exec()

    def apply_in_game_settings_safely(self, dialog, model_name, temperature, top_p, response_length, max_tokens):
        """Apply settings from the in-game dialog with extra safety checks"""
        try:
            # Check again if generation is running (in case it started during dialog)
            if hasattr(self, 'generation_thread') and self.generation_thread.isRunning():
                QMessageBox.warning(self, "Settings Locked",
                                    "Cannot apply settings while text generation is in progress.")
                return

            # Store values in game state
            self.game_state['game_info']['model_name'] = model_name
            self.game_state['game_info']['temperature'] = temperature
            self.game_state['game_info']['top_p'] = top_p
            self.game_state['game_info']['response_length'] = response_length
            self.game_state['game_info']['max_tokens'] = max_tokens

            # Save the game state
            rpg_engine.save_game_state(self.game_state, self.story_name)

            # Handle model changes more carefully
            if self.model:
                model_changed = model_name != self.model.model_name
                if model_changed:
                    # Create a new model instance if the model name changed
                    try:
                        new_model = rpg_engine.OllamaLLM(
                            model=model_name,
                            temperature=temperature,
                            top_p=top_p,
                            max_tokens=max_tokens
                        )
                        # Only replace if successfully created
                        self.model = new_model
                    except Exception as e:
                        QMessageBox.warning(self, "Model Change Failed",
                                            f"Failed to change model: {str(e)}\nOther settings were applied.")
                else:
                    # Update settings on existing model
                    self.model.update_settings(
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens
                    )

            # Get user-friendly descriptions
            length_labels = {
                1: "Very Brief",
                2: "Brief",
                3: "Medium",
                4: "Detailed",
                5: "Very Detailed"
            }
            response_length_text = length_labels.get(response_length, "Medium")

            # Show confirmation in game display
            self.text_display.append_system_message(
                f"AI settings updated: Temperature={temperature:.1f}, Response Length={response_length_text}, Max Tokens={max_tokens}")

            # Update the settings tab if it's open
            self.update_ai_settings_state()

            # Close dialog
            dialog.accept()

        except Exception as e:
            # Catch any exceptions to prevent crash
            QMessageBox.critical(self, "Settings Error",
                                 f"An error occurred while applying settings: {str(e)}\nYour game is still running.")
            print(f"Settings error: {e}")


    def apply_quick_settings(self, dialog, model_name, temperature):

        """Apply settings from the quick settings dialog"""

        # Check if model has changed

        model_changed = model_name != self.game_state['game_info'].get('model_name', 'mistral-small')



        # Store values in game state

        self.game_state['game_info']['model_name'] = model_name

        self.game_state['game_info']['temperature'] = temperature



        # Save the game state

        rpg_engine.save_game_state(self.game_state, self.story_name)



        # Update the model

        if self.model:

            if model_changed:

                # Create a new model instance if the model name changed

                self.model.change_model(model_name)



            # Update settings

            self.model.update_settings(temperature=temperature)



        # Show confirmation in game

        if model_changed:

            self.text_display.append_system_message(f"AI model changed to {model_name}")

        self.text_display.append_system_message(f"AI temperature set to {temperature:.1f}")



        # Update settings tab if open

        self.update_ai_settings_state()



        # Close dialog

        dialog.accept()



    def show_ai_settings(self):

        """Show the AI settings tab"""

        self.tabs.setTabVisible(4, True)

        self.tabs.setCurrentIndex(4)

        self.update_ai_settings_state()



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

        stories = rpg_engine.list_stories()



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

                if rpg_engine.delete_story(file_name):

                    QMessageBox.information(self, "Success", f"Story '{story_title}' deleted successfully.")

                    self.refresh_stories_list()

                else:

                    QMessageBox.warning(self, "Error", f"Failed to delete story '{story_title}'.")

        else:

            QMessageBox.warning(self, "Invalid Story", "Could not parse the story information.")



    def create_new_story(self, player_input):

        """Create a new story from the wizard input with AI settings"""

        if player_input is None:

            # User clicked back

            self.tabs.setTabVisible(2, False)

            self.tabs.setCurrentIndex(0)

            return



        # Initialize the game state

        self.game_state = rpg_engine.init_game_state(player_input)

        self.story_name = player_input["story_title"]



        # Add AI settings to game state

        self.game_state['game_info']['temperature'] = 0.7  # Default temperature

        self.game_state['game_info']['top_p'] = 0.9  # Default top_p

        self.game_state['game_info']['max_tokens'] = 2048  # Default max tokens



        # Initialize the model with settings

        model_name = self.game_state["game_info"]["model_name"]

        self.model = rpg_engine.OllamaLLM(

            model=model_name,

            temperature=self.game_state['game_info']['temperature'],

            top_p=self.game_state['game_info']['top_p'],

            max_tokens=self.game_state['game_info']['max_tokens']

        )



        # Generate initial context

        context = rpg_engine.generate_context(self.game_state)

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

        initial_memory, _ = rpg_engine.extract_memory_updates(

            initial_prompt,

            response,

            self.game_state['narrative_memory'],

            self.model,

            self.game_state['game_info']['plot_pace']

        )



        # Update memory

        for category, items in initial_memory.items():

            if category not in self.game_state['narrative_memory']:

                self.game_state['narrative_memory'][category] = []

            self.game_state['narrative_memory'][category].extend(items)



        # Save the initial game state

        rpg_engine.save_game_state(self.game_state, self.story_name)



        # Enable the input field

        self.input_field.setEnabled(True)

        self.send_button.setEnabled(True)

        self.input_field.setFocus()



    def load_story(self, file_name):

        """Load a story from a file with AI settings support"""

        # Load the game state

        self.game_state = rpg_engine.load_game_state(file_name)



        if not self.game_state:

            QMessageBox.warning(self, "Error", "Failed to load the story. The save file might be corrupted.")

            return



        self.story_name = self.game_state['game_info']['title']



        # Add AI settings if not present (for backwards compatibility)

        if 'temperature' not in self.game_state['game_info']:

            self.game_state['game_info']['temperature'] = 0.7



        if 'top_p' not in self.game_state['game_info']:

            self.game_state['game_info']['top_p'] = 0.9



        if 'max_tokens' not in self.game_state['game_info']:

            self.game_state['game_info']['max_tokens'] = 2048



        # Initialize the model with settings

        model_name = self.game_state["game_info"].get("model_name", "mistral-small")

        self.model = rpg_engine.OllamaLLM(

            model=model_name,

            temperature=self.game_state['game_info']['temperature'],

            top_p=self.game_state['game_info']['top_p'],

            max_tokens=self.game_state['game_info']['max_tokens']

        )



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

                "conversation_details": [],

                "new_npcs": [],

                "new_locations": [],

                "new_items": [],

                "new_quests": []

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

                    memory_updates, _ = rpg_engine.extract_memory_updates(

                        player_input,

                        dm_response,

                        self.game_state['narrative_memory'],

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



        # Add new memory categories if missing (for backwards compatibility)

        for category in ['environment_details', 'conversation_details',

                         'new_npcs', 'new_locations', 'new_items', 'new_quests']:

            if category not in self.game_state['narrative_memory']:

                self.game_state['narrative_memory'][category] = []



        # Clear the text display

        self.text_display.clear()



        # Display the conversation history

        self.text_display.append_system_message(f"Loaded story: {self.story_name}")

        self.text_display.append_system_message(

            f"Using AI model: {model_name} (Temperature: {self.game_state['game_info']['temperature']:.1f})")



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



        # Update AI settings tab

        self.update_ai_settings_state()



        # Show the game tab

        self.tabs.setTabVisible(1, True)

        self.tabs.setCurrentIndex(1)



        # Enable the input field

        self.input_field.setEnabled(True)

        self.send_button.setEnabled(True)

        self.input_field.setFocus()

    def process_input(self):
        """Process the player input"""
        self.generation_in_progress = True
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
        context = rpg_engine.generate_context(self.game_state)

        # Setup prompt variables
        prompt_vars = {
            'genre': self.game_state['game_info']['genre'],
            'world_name': self.game_state['game_info']['world_name'],
            'setting_description': self.game_state['game_info']['setting'],
            'tone': self.game_state['game_info']['tone'],
            'rating': self.game_state['game_info']['rating'],
            'plot_pace': self.game_state['game_info'].get('plot_pace', 'Balanced'),
            'context': context,
            'question': player_input,
            'game_info': self.game_state['game_info']  # Pass the entire game_info to include response_length
        }

        # Start the generation thread
        self.text_display.stream_text("DM: ", "dm_name")

        self.generation_thread = ModelGenerationThread(self.model, prompt_vars)
        self.generation_thread.text_generated.connect(lambda text: self.text_display.stream_text(text, "dm_text"))
        self.generation_thread.generation_complete.connect(
            lambda response: self.finalize_response(player_input, response))
        self.generation_thread.start()

    def finalize_response(self, player_input, response):
        """Finalize the response from the model with immersion protection"""
        self.generation_in_progress = False
        # Check for out-of-character AI responses
        ai_phrases = [
            "as an ai", "i cannot", "i'm not able to", "i apologize",
            "ai model", "language model", "i'm sorry", "i can't create",
            "i cannot generate", "against my ethical guidelines",
            "Error:", "DM:", "Player:"
        ]

        # Filter out non-immersive responses
        filtered_response = response
        for phrase in ai_phrases:
            if phrase in filtered_response.lower():
                # Replace with an appropriate in-character response
                filtered_response = filtered_response.replace(phrase, "")

        # Add a newline
        self.text_display.stream_text("\n", "dm_text")

        # Create the thread and worker for background processing
        self.update_thread = QThread()
        self.update_worker = GameStateUpdateWorker(self.game_state, player_input, response, self.model)
        self.update_worker.moveToThread(self.update_thread)

        # Connect signals and slots
        self.update_thread.started.connect(self.update_worker.update_game_state)
        self.update_worker.update_complete.connect(self.handle_game_state_update)
        self.update_worker.update_complete.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.finished.connect(self.update_worker.deleteLater)

        # Enable the input field immediately so the user can type while processing happens
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

        # Start the thread
        self.update_thread.start()

    def handle_game_state_update(self, updated_game_state, important_updates):
        """Handle the completion of game state updates"""
        # Update the game state reference
        self.game_state = updated_game_state

        # Update the game status panel
        self.update_game_status()

        # Show any important updates if needed
        # Uncomment if you want to notify the player of important events
        # if important_updates:
        #    for update in important_updates:
        #        self.text_display.append_system_message(update)

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
        memory_updates, important_updates = rpg_engine.extract_memory_updates(
            player_input,
            dm_response,
            self.game_state['narrative_memory'],
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

        # Dynamic element creation from the rpg_engine.py functions
        self.game_state = rpg_engine.update_dynamic_elements(self.game_state, memory_updates)

        # Store important updates (but don't display them)
        if important_updates:
            self.game_state['important_updates'] = important_updates

        # Save the game state
        rpg_engine.save_game_state(self.game_state, self.story_name)

        # Update the game status panel
        self.update_game_status()

    def update_game_status(self):
        """Update the game status panel with clickable elements"""
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

        # Update locations list
        self.locations_list.clear()
        for loc_id, loc in self.game_state['locations'].items():
            if loc['visited']:
                self.locations_list.addItem(loc['name'])

        # Update quests list
        self.quests_list.clear()
        pc = self.game_state['player_characters'][pc_id]
        for quest_id in pc['quests']:
            if quest_id in self.game_state['quests']:
                quest = self.game_state['quests'][quest_id]
                status_icon = "✓" if quest['status'] == "completed" else "⚠" if quest['status'] == "active" else "?"
                self.quests_list.addItem(f"{status_icon} {quest['name']}")



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

    def show_npc_details(self, item):
        """Show detailed information about the selected NPC"""
        if not self.game_state:
            return

        # Extract NPC name from the list item text (removing any status)
        npc_name = item.text().split(" - ")[0].strip()

        # Find the NPC in the game state
        npc_data = None
        npc_id = None
        for id, npc in self.game_state['npcs'].items():
            if npc['name'] == npc_name:
                npc_data = npc
                npc_id = id
                break

        if not npc_data:
            return

        # Create a dialog to display NPC details
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle(f"Character: {npc_name}")
        details_dialog.setMinimumSize(500, 400)
        details_dialog.setStyleSheet(f"background-color: {BG_COLOR};")

        layout = QVBoxLayout(details_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create scrollable area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)

        # NPC portrait/image placeholder
        portrait_label = QLabel()
        portrait_label.setFixedSize(150, 150)
        portrait_label.setStyleSheet(f"background-color: {DM_NAME_COLOR}; border-radius: 75px;")
        portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        portrait_label.setText(npc_name[0].upper())  # First letter as placeholder

        font = QFont()
        font.setPointSize(40)
        font.setBold(True)
        portrait_label.setFont(font)
        portrait_label.setStyleSheet(f"color: white; background-color: {DM_NAME_COLOR}; border-radius: 75px;")

        # Center the portrait
        portrait_layout = QHBoxLayout()
        portrait_layout.addStretch(1)
        portrait_layout.addWidget(portrait_label)
        portrait_layout.addStretch(1)
        scroll_layout.addLayout(portrait_layout)

        # NPC details in styled sections
        section_style = f"""
            QLabel {{
                color: {HIGHLIGHT_COLOR};
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 5px;
                border-bottom: 1px solid {DM_NAME_COLOR};
            }}
        """

        content_style = f"""
            QLabel {{
                color: #3A1E64;
                font-size: 14px;
                padding: 5px;
                background-color: white;
                border-radius: 5px;
            }}
        """

        # Basic info section
        basic_info_label = QLabel("Basic Information")
        basic_info_label.setStyleSheet(section_style)
        scroll_layout.addWidget(basic_info_label)

        basic_info = f"""
        <b>Name:</b> {npc_data['name']}<br>
        <b>Race:</b> {npc_data['race']}<br>
        <b>Disposition:</b> {npc_data['disposition']}<br>
        <b>Current Location:</b> {self.game_state['locations'][npc_data['location']]['name']}<br>
        """

        basic_info_content = QLabel()
        basic_info_content.setTextFormat(Qt.TextFormat.RichText)
        basic_info_content.setText(basic_info)
        basic_info_content.setStyleSheet(content_style)
        basic_info_content.setWordWrap(True)
        scroll_layout.addWidget(basic_info_content)

        # Description section
        description_label = QLabel("Description")
        description_label.setStyleSheet(section_style)
        scroll_layout.addWidget(description_label)

        description_content = QLabel(npc_data['description'])
        description_content.setStyleSheet(content_style)
        description_content.setWordWrap(True)
        scroll_layout.addWidget(description_content)

        # Personality section
        personality_label = QLabel("Personality & Motivation")
        personality_label.setStyleSheet(section_style)
        scroll_layout.addWidget(personality_label)

        personality_content = QLabel(f"""
        <b>Motivation:</b> {npc_data['motivation']}<br>
        <b>Dialogue Style:</b> {npc_data['dialogue_style']}<br>
        """)
        personality_content.setTextFormat(Qt.TextFormat.RichText)
        personality_content.setStyleSheet(content_style)
        personality_content.setWordWrap(True)
        scroll_layout.addWidget(personality_content)

        # Knowledge section if available
        if npc_data['knowledge']:
            knowledge_label = QLabel("Knowledge")
            knowledge_label.setStyleSheet(section_style)
            scroll_layout.addWidget(knowledge_label)

            knowledge_text = "<ul>"
            for knowledge_item in npc_data['knowledge']:
                knowledge_text += f"<li>{knowledge_item}</li>"
            knowledge_text += "</ul>"

            knowledge_content = QLabel(knowledge_text)
            knowledge_content.setTextFormat(Qt.TextFormat.RichText)
            knowledge_content.setStyleSheet(content_style)
            knowledge_content.setWordWrap(True)
            scroll_layout.addWidget(knowledge_content)

        # Relationships section if available
        if npc_data['relationships']:
            relationships_label = QLabel("Relationships")
            relationships_label.setStyleSheet(section_style)
            scroll_layout.addWidget(relationships_label)

            relationships_text = "<ul>"
            for rel_name, rel_type in npc_data['relationships'].items():
                relationships_text += f"<li><b>{rel_name}:</b> {rel_type}</li>"
            relationships_text += "</ul>"

            relationships_content = QLabel(relationships_text)
            relationships_content.setTextFormat(Qt.TextFormat.RichText)
            relationships_content.setStyleSheet(content_style)
            relationships_content.setWordWrap(True)
            scroll_layout.addWidget(relationships_content)

        # Narrative memory related to this NPC
        memory_entries = []

        # Check each memory category for mentions of this NPC
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if npc_name.lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Narrative Memory")
            memory_label.setStyleSheet(section_style)
            scroll_layout.addWidget(memory_label)

            memory_text = "<ul>"
            for entry in memory_entries:
                memory_text += f"<li>{entry}</li>"
            memory_text += "</ul>"

            memory_content = QLabel(memory_text)
            memory_content.setTextFormat(Qt.TextFormat.RichText)
            memory_content.setStyleSheet(content_style)
            memory_content.setWordWrap(True)
            scroll_layout.addWidget(memory_content)

        # Finish setting up the scroll area
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Add a close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR}; 
                color: white; 
                border-radius: 6px; 
                padding: 10px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}
        """)
        close_button.clicked.connect(details_dialog.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        # Show the dialog
        details_dialog.exec()

    def show_location_details(self, item):
        """Show detailed information about the selected location"""
        if not self.game_state:
            return

        # Extract location name from the list item
        location_name = item.text()

        # Find the location in the game state
        location_data = None
        location_id = None
        for id, location in self.game_state['locations'].items():
            if location['name'] == location_name:
                location_data = location
                location_id = id
                break

        if not location_data:
            return

        # Create a dialog to display location details
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle(f"Location: {location_name}")
        details_dialog.setMinimumSize(500, 400)
        details_dialog.setStyleSheet(f"background-color: {BG_COLOR};")

        layout = QVBoxLayout(details_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create scrollable area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)

        # Location header
        header_label = QLabel(location_name)
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; margin-bottom: 10px;")
        scroll_layout.addWidget(header_label)

        # Location details in styled sections
        section_style = f"""
            QLabel {{
                color: {HIGHLIGHT_COLOR};
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 5px;
                border-bottom: 1px solid {DM_NAME_COLOR};
            }}
        """

        content_style = f"""
            QLabel {{
                color: #3A1E64;
                font-size: 14px;
                padding: 5px;
                background-color: white;
                border-radius: 5px;
            }}
        """

        # Description section
        description_label = QLabel("Description")
        description_label.setStyleSheet(section_style)
        scroll_layout.addWidget(description_label)

        description_content = QLabel(location_data['description'])
        description_content.setStyleSheet(content_style)
        description_content.setWordWrap(True)
        scroll_layout.addWidget(description_content)

        # Ambience section
        ambience_label = QLabel("Ambience")
        ambience_label.setStyleSheet(section_style)
        scroll_layout.addWidget(ambience_label)

        ambience_content = QLabel(location_data['ambience'])
        ambience_content.setStyleSheet(content_style)
        ambience_content.setWordWrap(True)
        scroll_layout.addWidget(ambience_content)

        # Connected locations section
        connected_label = QLabel("Connected Locations")
        connected_label.setStyleSheet(section_style)
        scroll_layout.addWidget(connected_label)

        connected_text = "<ul>"
        if location_data['connected_to']:
            for connected_id in location_data['connected_to']:
                if connected_id in self.game_state['locations']:
                    connected_text += f"<li>{self.game_state['locations'][connected_id]['name']}</li>"
        else:
            connected_text += "<li>No connected locations</li>"
        connected_text += "</ul>"

        connected_content = QLabel(connected_text)
        connected_content.setTextFormat(Qt.TextFormat.RichText)
        connected_content.setStyleSheet(content_style)
        connected_content.setWordWrap(True)
        scroll_layout.addWidget(connected_content)

        # NPCs present section
        npcs_label = QLabel("NPCs Present")
        npcs_label.setStyleSheet(section_style)
        scroll_layout.addWidget(npcs_label)

        npcs_text = "<ul>"
        if location_data['npcs_present']:
            for npc_id in location_data['npcs_present']:
                if npc_id in self.game_state['npcs']:
                    npc = self.game_state['npcs'][npc_id]
                    npcs_text += f"<li><b>{npc['name']}</b> - {npc['disposition']}</li>"
        else:
            npcs_text += "<li>No NPCs present</li>"
        npcs_text += "</ul>"

        npcs_content = QLabel(npcs_text)
        npcs_content.setTextFormat(Qt.TextFormat.RichText)
        npcs_content.setStyleSheet(content_style)
        npcs_content.setWordWrap(True)
        scroll_layout.addWidget(npcs_content)

        # Points of interest section
        if location_data['points_of_interest']:
            poi_label = QLabel("Points of Interest")
            poi_label.setStyleSheet(section_style)
            scroll_layout.addWidget(poi_label)

            poi_text = "<ul>"
            for poi in location_data['points_of_interest']:
                poi_text += f"<li>{poi.replace('_', ' ').title()}</li>"
            poi_text += "</ul>"

            poi_content = QLabel(poi_text)
            poi_content.setTextFormat(Qt.TextFormat.RichText)
            poi_content.setStyleSheet(content_style)
            poi_content.setWordWrap(True)
            scroll_layout.addWidget(poi_content)

        # Available quests section
        if location_data['available_quests']:
            quests_label = QLabel("Available Quests")
            quests_label.setStyleSheet(section_style)
            scroll_layout.addWidget(quests_label)

            quests_text = "<ul>"
            for quest_id in location_data['available_quests']:
                if quest_id in self.game_state['quests']:
                    quest = self.game_state['quests'][quest_id]
                    quests_text += f"<li><b>{quest['name']}</b> - {quest['description']}</li>"
            quests_text += "</ul>"

            quests_content = QLabel(quests_text)
            quests_content.setTextFormat(Qt.TextFormat.RichText)
            quests_content.setStyleSheet(content_style)
            quests_content.setWordWrap(True)
            scroll_layout.addWidget(quests_content)

        # Narrative memory related to this location
        memory_entries = []

        # Check each memory category for mentions of this location
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if location_name.lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Narrative Memory")
            memory_label.setStyleSheet(section_style)
            scroll_layout.addWidget(memory_label)

            memory_text = "<ul>"
            for entry in memory_entries:
                memory_text += f"<li>{entry}</li>"
            memory_text += "</ul>"

            memory_content = QLabel(memory_text)
            memory_content.setTextFormat(Qt.TextFormat.RichText)
            memory_content.setStyleSheet(content_style)
            memory_content.setWordWrap(True)
            scroll_layout.addWidget(memory_content)

        # Finish setting up the scroll area
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Add interactive buttons
        button_layout = QHBoxLayout()

        # Add a travel button if not current location
        if location_id != self.game_state['game_info']['current_location']:
            travel_button = QPushButton("Travel Here")
            travel_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR}; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 10px;
                    font-weight: bold;
                    min-width: 100px;
                }}
                QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}
            """)
            travel_button.clicked.connect(lambda: self.travel_to_location(location_id, details_dialog))
            button_layout.addWidget(travel_button)

        # Add close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR}; 
                color: white; 
                border-radius: 6px; 
                padding: 10px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}
        """)
        close_button.clicked.connect(details_dialog.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # Show the dialog
        details_dialog.exec()

    def show_quest_details(self, item):
        """Show detailed information about the selected quest"""
        if not self.game_state:
            return

        # Extract quest name from the list item (remove status icon)
        quest_text = item.text()
        if quest_text.startswith("✓ ") or quest_text.startswith("⚠ ") or quest_text.startswith("? "):
            quest_name = quest_text[2:].strip()
        else:
            quest_name = quest_text

        # Find the quest in the game state
        quest_data = None
        quest_id = None
        for id, quest in self.game_state['quests'].items():
            if quest['name'] == quest_name:
                quest_data = quest
                quest_id = id
                break

        if not quest_data:
            return

        # Create a dialog to display quest details
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle(f"Quest: {quest_name}")
        details_dialog.setMinimumSize(500, 400)
        details_dialog.setStyleSheet(f"background-color: {BG_COLOR};")

        layout = QVBoxLayout(details_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create scrollable area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)

        # Quest header with status
        status_text = ""
        if quest_data['status'] == "active":
            status_text = " (Active)"
            status_color = "#FF9800"  # Orange
        elif quest_data['status'] == "completed":
            status_text = " (Completed)"
            status_color = "#4CAF50"  # Green
        else:
            status_text = " (Inactive)"
            status_color = "#9E9E9E"  # Gray

        header_label = QLabel(f"{quest_name}{status_text}")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet(f"color: {status_color}; margin-bottom: 10px;")
        scroll_layout.addWidget(header_label)

        # Quest details in styled sections
        section_style = f"""
            QLabel {{
                color: {HIGHLIGHT_COLOR};
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 5px;
                border-bottom: 1px solid {DM_NAME_COLOR};
            }}
        """

        content_style = f"""
            QLabel {{
                color: #3A1E64;
                font-size: 14px;
                padding: 5px;
                background-color: white;
                border-radius: 5px;
            }}
        """

        # Description section
        description_label = QLabel("Description")
        description_label.setStyleSheet(section_style)
        scroll_layout.addWidget(description_label)

        description_content = QLabel(quest_data['description'])
        description_content.setStyleSheet(content_style)
        description_content.setWordWrap(True)
        scroll_layout.addWidget(description_content)

        # Quest giver section
        giver_label = QLabel("Quest Giver")
        giver_label.setStyleSheet(section_style)
        scroll_layout.addWidget(giver_label)

        giver_name = quest_data['giver']
        # Try to find the NPC if it's not "narrator"
        if giver_name != "narrator":
            for npc_id, npc in self.game_state['npcs'].items():
                if npc_id == giver_name or npc['name'].lower() == giver_name.lower():
                    giver_name = npc['name']
                    break

        giver_content = QLabel(giver_name.title())
        giver_content.setStyleSheet(content_style)
        giver_content.setWordWrap(True)
        scroll_layout.addWidget(giver_content)

        # Quest steps section
        steps_label = QLabel("Quest Steps")
        steps_label.setStyleSheet(section_style)
        scroll_layout.addWidget(steps_label)

        steps_text = "<ul>"
        for step in quest_data['steps']:
            check = "✓" if step.get('completed', False) else "□"
            steps_text += f"<li><b>{check}</b> {step['description']}</li>"
        steps_text += "</ul>"

        steps_content = QLabel(steps_text)
        steps_content.setTextFormat(Qt.TextFormat.RichText)
        steps_content.setStyleSheet(content_style)
        steps_content.setWordWrap(True)
        scroll_layout.addWidget(steps_content)

        # Additional details section
        details_label = QLabel("Additional Details")
        details_label.setStyleSheet(section_style)
        scroll_layout.addWidget(details_label)

        details_text = f"""
        <b>Difficulty:</b> {quest_data.get('difficulty', 'Standard')}<br>
        <b>Time Sensitive:</b> {'Yes' if quest_data.get('time_sensitive', False) else 'No'}<br>
        """

        details_content = QLabel(details_text)
        details_content.setTextFormat(Qt.TextFormat.RichText)
        details_content.setStyleSheet(content_style)
        details_content.setWordWrap(True)
        scroll_layout.addWidget(details_content)

        # Narrative memory related to this quest
        memory_entries = []

        # Check each memory category for mentions of this quest
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if quest_name.lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Narrative Memory")
            memory_label.setStyleSheet(section_style)
            scroll_layout.addWidget(memory_label)

            memory_text = "<ul>"
            for entry in memory_entries:
                memory_text += f"<li>{entry}</li>"
            memory_text += "</ul>"

            memory_content = QLabel(memory_text)
            memory_content.setTextFormat(Qt.TextFormat.RichText)
            memory_content.setStyleSheet(content_style)
            memory_content.setWordWrap(True)
            scroll_layout.addWidget(memory_content)

        # Finish setting up the scroll area
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Add a close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR}; 
                color: white; 
                border-radius: 6px; 
                padding: 10px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}
        """)
        close_button.clicked.connect(details_dialog.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        # Show the dialog
        details_dialog.exec()

    def travel_to_location(self, location_id, parent_dialog=None):
        """Travel to the specified location"""
        if not self.game_state or location_id not in self.game_state['locations']:
            return

        # Check if location is connected to current location
        current_loc_id = self.game_state['game_info']['current_location']
        current_loc = self.game_state['locations'][current_loc_id]

        if location_id not in current_loc['connected_to']:
            QMessageBox.warning(self, "Travel Error",
                                "You cannot travel directly to this location. It is not connected to your current location.")
            return

        # Update current location
        self.game_state['game_info']['current_location'] = location_id

        # Mark location as visited
        self.game_state['locations'][location_id]['visited'] = True

        # Add travel message to display
        location_name = self.game_state['locations'][location_id]['name']
        self.text_display.append_system_message(f"You travel to {location_name}.")

        # Update the game status
        self.update_game_status()

        # Close parent dialog if provided
        if parent_dialog:
            parent_dialog.accept()



    def save_game(self):

        """Save the game"""

        if self.game_state and self.story_name:

            rpg_engine.save_game_state(self.game_state, self.story_name)

            self.text_display.append_system_message("Game saved!")



    def show_memory(self):

        """Show the narrative memory"""

        if not self.game_state:

            return



        memory_dialog = QDialog(self)

        memory_dialog.setWindowTitle("Narrative Memory")

        memory_dialog.setMinimumSize(600, 500)

        memory_dialog.setStyleSheet(f"background-color: {BG_COLOR};")



        layout = QVBoxLayout(memory_dialog)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(15)



        memory_text = QTextBrowser()

        memory_text.setStyleSheet(f"""

                QTextBrowser {{

                    background-color: white;

                    border: 1px solid {DM_NAME_COLOR};

                    border-radius: 8px;

                    padding: 15px;

                    color: #3A1E64;

                }}

            """)



        # Add memory categories

        memory = self.game_state['narrative_memory']



        memory_html = "<h2 style='color: #7E57C2;'>Narrative Memory</h2>"



        # World facts

        if memory['world_facts']:

            memory_html += "<h3 style='color: #4A2D7D;'>World Facts:</h3><ul>"

            for item in memory['world_facts']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Character development

        if memory['character_development']:

            memory_html += "<h3 style='color: #4A2D7D;'>Character Development:</h3><ul>"

            for item in memory['character_development']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Relationships

        if memory['relationships']:

            memory_html += "<h3 style='color: #4A2D7D;'>Relationships:</h3><ul>"

            for item in memory['relationships']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Plot developments

        if memory['plot_developments']:

            memory_html += "<h3 style='color: #4A2D7D;'>Plot Developments:</h3><ul>"

            for item in memory['plot_developments']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Player decisions

        if memory['player_decisions']:

            memory_html += "<h3 style='color: #4A2D7D;'>Important Player Decisions:</h3><ul>"

            for item in memory['player_decisions']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Environment details

        if memory.get('environment_details', []):

            memory_html += "<h3 style='color: #4A2D7D;'>Environment Details:</h3><ul>"

            for item in memory['environment_details']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # Conversation details

        if memory.get('conversation_details', []):

            memory_html += "<h3 style='color: #4A2D7D;'>Conversation Details:</h3><ul>"

            for item in memory['conversation_details']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # New NPCs

        if memory.get('new_npcs', []):

            memory_html += "<h3 style='color: #4A2D7D;'>New Characters:</h3><ul>"

            for item in memory['new_npcs']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # New locations

        if memory.get('new_locations', []):

            memory_html += "<h3 style='color: #4A2D7D;'>New Locations:</h3><ul>"

            for item in memory['new_locations']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # New items

        if memory.get('new_items', []):

            memory_html += "<h3 style='color: #4A2D7D;'>New Items:</h3><ul>"

            for item in memory['new_items']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        # New quests

        if memory.get('new_quests', []):

            memory_html += "<h3 style='color: #4A2D7D;'>New Quests:</h3><ul>"

            for item in memory['new_quests']:

                memory_html += f"<li style='color: #3A1E64; margin-bottom: 5px;'>{item}</li>"

            memory_html += "</ul>"



        memory_text.setHtml(memory_html)

        layout.addWidget(memory_text)



        close_button = QPushButton("Close")

        close_button.setStyleSheet(f"""

                QPushButton {{

                    background-color: {ACCENT_COLOR}; 

                    color: white; 

                    border-radius: 6px; 

                    padding: 10px;

                    font-weight: bold;

                    min-width: 120px;

                }}

                QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

            """)

        close_button.clicked.connect(memory_dialog.accept)



        button_layout = QHBoxLayout()

        button_layout.addStretch(1)

        button_layout.addWidget(close_button)

        button_layout.addStretch(1)



        layout.addLayout(button_layout)



        memory_dialog.exec()



    def show_summary(self):

        """Show a summary of the story so far"""

        if not self.game_state:

            return



        summary_dialog = QDialog(self)

        summary_dialog.setWindowTitle("Story Summary")

        summary_dialog.setMinimumSize(600, 400)

        summary_dialog.setStyleSheet(f"background-color: {BG_COLOR};")



        layout = QVBoxLayout(summary_dialog)

        layout.setContentsMargins(20, 20, 20, 20)

        layout.setSpacing(15)



        # Add a header

        header_label = QLabel("The Story So Far...")

        header_font = QFont()

        header_font.setPointSize(18)

        header_font.setBold(True)

        header_label.setFont(header_font)

        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_label.setStyleSheet(f"color: {HIGHLIGHT_COLOR}; margin-bottom: 10px;")

        layout.addWidget(header_label)



        # Create a text display for the summary

        self.summary_text = QTextEdit()

        self.summary_text.setReadOnly(True)

        self.summary_text.setStyleSheet(f"""

                QTextEdit {{

                    background-color: white;

                    border: 1px solid {DM_NAME_COLOR};

                    border-radius: 8px;

                    padding: 15px;

                    color: #3A1E64;

                    font-size: 14px;

                }}

            """)

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

        close_button.setStyleSheet(f"""

                QPushButton {{

                    background-color: {ACCENT_COLOR}; 

                    color: white; 

                    border-radius: 6px; 

                    padding: 10px;

                    font-weight: bold;

                    min-width: 120px;

                }}

                QPushButton:hover {{ background-color: {HIGHLIGHT_COLOR}; }}

            """)

        close_button.clicked.connect(summary_dialog.accept)



        button_layout = QHBoxLayout()

        button_layout.addStretch(1)

        button_layout.addWidget(close_button)

        button_layout.addStretch(1)



        layout.addLayout(button_layout)



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

                        format.setForeground(QColor(HIGHLIGHT_COLOR))

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

            rpg_engine.save_game_state(self.game_state, self.story_name)



        # Reset the game state

        self.game_state = None

        self.story_name = None

        self.model = None



        # Hide the game tab

        self.tabs.setTabVisible(1, False)



        # Show the main menu

        self.tabs.setCurrentIndex(0)







def main_gui():

    """Main entry point for the GUI application"""

    app = QApplication(sys.argv)



    # Set app style

    app.setStyle("Fusion")



    window = LaceAIdventureGUI()

    window.show()



    sys.exit(app.exec())



if __name__ == "__main__":

    main_gui()