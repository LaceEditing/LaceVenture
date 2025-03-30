import sys
import os
import re
import hashlib
import json
import glob
from functools import lru_cache

from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel,
                             QComboBox, QListWidget, QMessageBox, QFormLayout, QSpinBox,
                             QSplitter, QScrollArea, QFrame, QDialog, QDialogButtonBox,
                             QCheckBox, QTextBrowser, QGroupBox)
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

    def run(self):
        """Run the model generation"""
        try:
            prompt = rpg_engine.ChatPromptTemplate.from_template(rpg_engine.dm_template)
            chain = prompt | self.model

            # Stream the response token by token
            for chunk in chain.stream(self.prompt_vars):
                # Extract text from chunk (handling different possible formats)
                try:
                    if hasattr(chunk, 'content'):
                        chunk_text = str(chunk.content)
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        chunk_text = str(chunk['content'])
                    else:
                        chunk_text = str(chunk)

                    # Emit the generated text and add to full response
                    self.text_generated.emit(chunk_text)
                    self.full_response += chunk_text
                except Exception as e:
                    pass  # Skip any problematic chunks

        except Exception as e:
            # Fall back to standard generation if streaming fails
            try:
                prompt = rpg_engine.ChatPromptTemplate.from_template(rpg_engine.dm_template)
                chain = prompt | self.model
                self.full_response = chain.invoke(self.prompt_vars)
                self.text_generated.emit(self.full_response)
            except Exception as e2:
                self.text_generated.emit(f"\nError generating response: {str(e2)}")

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


class LaceAIdventureGUI(QMainWindow):
    """Main window for the adventure game"""

    def __init__(self):
        super().__init__()
        self.game_state = None
        self.story_name = None
        self.model = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the main UI components"""
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

        # Add the tabs to the tab widget
        self.tabs.addTab(self.main_menu_tab, "Main Menu")
        self.tabs.addTab(self.game_tab, "Game")
        self.tabs.addTab(self.story_creation_tab, "Create Story")
        self.tabs.addTab(self.story_management_tab, "Manage Stories")

        # Add the tab widget to the main layout
        main_layout.addWidget(self.tabs)

        # Start with the main menu and hide other tabs
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabVisible(1, False)  # Hide game tab initially
        self.tabs.setTabVisible(2, False)  # Hide story creation tab initially
        self.tabs.setTabVisible(3, False)  # Hide story management tab initially

    def create_main_menu_tab(self):
        """Create the main menu interface"""
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

        exit_button = QPushButton("Exit")
        exit_button.setMinimumHeight(60)
        exit_button.setStyleSheet(button_style)

        # Connect signals to slots
        new_story_button.clicked.connect(self.show_story_creation)
        load_story_button.clicked.connect(self.show_story_load)
        manage_stories_button.clicked.connect(self.show_story_management)
        exit_button.clicked.connect(self.close)

        # Add buttons to layout
        button_layout.addWidget(new_story_button)
        button_layout.addWidget(load_story_button)
        button_layout.addWidget(manage_stories_button)
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
        """Create a new story from the wizard input"""
        # Initialize the game state
        self.game_state = rpg_engine.init_game_state(player_input)
        self.story_name = player_input["story_title"]

        # Initialize the model
        self.model = rpg_engine.OllamaLLM(model=self.game_state["game_info"]["model_name"])

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
        """Load a story from a file"""
        # Load the game state
        self.game_state = rpg_engine.load_game_state(file_name)

        if not self.game_state:
            QMessageBox.warning(self, "Error", "Failed to load the story. The save file might be corrupted.")
            return

        self.story_name = self.game_state['game_info']['title']

        # Initialize the model
        model_name = self.game_state["game_info"].get("model_name", "mistral-small")
        self.model = rpg_engine.OllamaLLM(model=model_name)

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

        # Show the game tab
        self.tabs.setTabVisible(1, True)
        self.tabs.setCurrentIndex(1)

        # Enable the input field
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

    def process_input(self):
        """Process the player input"""
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
            'question': player_input
        }

        # Start the generation thread
        self.text_display.stream_text("DM: ", "dm_name")

        self.generation_thread = ModelGenerationThread(self.model, prompt_vars)
        self.generation_thread.text_generated.connect(lambda text: self.text_display.stream_text(text, "dm_text"))
        self.generation_thread.generation_complete.connect(
            lambda response: self.finalize_response(player_input, response))
        self.generation_thread.start()

    def finalize_response(self, player_input, response):
        """Finalize the response from the model"""
        # Add a newline
        self.text_display.stream_text("\n", "dm_text")

        # Update the game state
        self.update_game_state(player_input, response)

        # Re-enable the input field
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

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

        # Store important updates
        if important_updates:
            self.game_state['important_updates'] = important_updates

            # Display important updates
            self.text_display.append_system_message("! Important developments:")
            for update in important_updates:
                self.text_display.append_system_message(f"* {update}")

        # Save the game state
        rpg_engine.save_game_state(self.game_state, self.story_name)

        # Update the game status panel
        self.update_game_status()

    def update_game_status(self):
        """Update the game status panel"""
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