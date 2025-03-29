import sys
import os
import json
import subprocess
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor, QIcon, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLineEdit,

                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget,

                             QLabel, QComboBox, QTabWidget, QSplitter,

                             QListWidget, QListWidgetItem, QScrollArea,

                             QFrame, QDialog, QMessageBox, QProgressBar,

                             QInputDialog, QCheckBox, QSlider, QSizePolicy, QAction, QMenu, QFormLayout,

                             QProgressDialog)
import requests

from memory_system import MemorySystem

from llm_interface import LLMInterface

from config import CAMPAIGNS_DIR, FREE_MODELS





class ModelLoadingThread(QThread):

    """Thread for loading the LLM model to prevent UI freezing."""

    finished = pyqtSignal(object)

    progress = pyqtSignal(str)

    error = pyqtSignal(str)



    def __init__(self, model_selection=None):

        super().__init__()

        self.model_selection = model_selection



    def run(self):

        try:

            # Update progress

            self.progress.emit("Initializing LLM interface...")



            # Initialize LLM based on selection

            if self.model_selection and "type" in self.model_selection:

                if self.model_selection["type"] == "local":

                    self.progress.emit(f"Loading local model: {os.path.basename(self.model_selection['path'])}")

                    llm = LLMInterface(provider="local")

                elif self.model_selection["type"] == "free":

                    model_name = self.model_selection["name"]

                    api_key = self.model_selection.get("api_key", "")

                    self.progress.emit(f"Connecting to {model_name}...")

                    llm = LLMInterface(api_key=api_key, selected_free_model=model_name)

                elif self.model_selection["type"] == "ollama":

                    model_name = self.model_selection["name"]

                    self.progress.emit(f"Connecting to Ollama with model: {model_name}")

                    llm = LLMInterface(provider="ollama", model=model_name)

                else:

                    self.progress.emit("Using default model from config...")

                    llm = LLMInterface()

            else:

                self.progress.emit("Using default model from config...")

                llm = LLMInterface()



            # Initialize memory system with the LLM

            self.progress.emit("Initializing memory system...")

            memory_system = MemorySystem(llm_interface=llm)



            # Signal completion

            self.finished.emit(memory_system)



        except Exception as e:

            self.error.emit(f"Error initializing system: {str(e)}")





class CharacterInfoWidget(QWidget):

    """Widget to display character information."""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setMinimumHeight(200)



        # Character name label

        self.name_label = QLabel("Character Name")

        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A5ACD;")

        self.layout.addWidget(self.name_label)



        # Character description

        self.description = QLabel("Description of the character...")

        self.description.setWordWrap(True)

        self.layout.addWidget(self.description)



        # Character traits

        self.traits_frame = QFrame()

        self.traits_frame.setFrameShape(QFrame.StyledPanel)

        self.traits_frame.setStyleSheet("background-color: #F0E6FF; border-radius: 5px;")

        self.traits_layout = QVBoxLayout(self.traits_frame)

        self.traits_label = QLabel("Traits")

        self.traits_label.setStyleSheet("font-weight: bold;")

        self.traits_layout.addWidget(self.traits_label)

        self.traits_content = QLabel("No traits available")

        self.traits_layout.addWidget(self.traits_content)

        self.layout.addWidget(self.traits_frame)



        # Character inventory

        self.inventory_frame = QFrame()

        self.inventory_frame.setFrameShape(QFrame.StyledPanel)

        self.inventory_frame.setStyleSheet("background-color: #F0E6FF; border-radius: 5px;")

        self.inventory_layout = QVBoxLayout(self.inventory_frame)

        self.inventory_label = QLabel("Inventory")

        self.inventory_label.setStyleSheet("font-weight: bold;")

        self.inventory_layout.addWidget(self.inventory_label)

        self.inventory_content = QLabel("No items available")

        self.inventory_layout.addWidget(self.inventory_content)

        self.layout.addWidget(self.inventory_frame)



        self.layout.addStretch()



    def update_info(self, character):

        """Update widget with character information."""

        if not character:

            self.name_label.setText("No Character Selected")

            self.description.setText("")

            self.traits_content.setText("No traits available")

            self.inventory_content.setText("No items available")

            return



        self.name_label.setText(character.name)

        self.description.setText(character.description)



        if hasattr(character, 'traits') and character.traits:

            traits_text = ""

            for trait, value in character.traits.items():

                traits_text += f"• <b>{trait.capitalize()}</b>: {value}<br>"

            self.traits_content.setText(traits_text)

        else:

            self.traits_content.setText("No traits available")



        if hasattr(character, 'inventory') and character.inventory:

            inventory_text = ""

            for item in character.inventory:

                inventory_text += f"• {item}<br>"

            self.inventory_content.setText(inventory_text)

        else:

            self.inventory_content.setText("No items available")





class LocationInfoWidget(QWidget):

    """Widget to display location information."""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setMinimumHeight(200)



        # Location name label

        self.name_label = QLabel("Location Name")

        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A5ACD;")

        self.layout.addWidget(self.name_label)



        # Location description

        self.description = QLabel("Description of the location...")

        self.description.setWordWrap(True)

        self.layout.addWidget(self.description)



        # Location features

        self.features_frame = QFrame()

        self.features_frame.setFrameShape(QFrame.StyledPanel)

        self.features_frame.setStyleSheet("background-color: #F0E6FF; border-radius: 5px;")

        self.features_layout = QVBoxLayout(self.features_frame)

        self.features_label = QLabel("Features")

        self.features_label.setStyleSheet("font-weight: bold;")

        self.features_layout.addWidget(self.features_label)

        self.features_content = QLabel("No features available")

        self.features_layout.addWidget(self.features_content)

        self.layout.addWidget(self.features_frame)



        # Characters present

        self.chars_frame = QFrame()

        self.chars_frame.setFrameShape(QFrame.StyledPanel)

        self.chars_frame.setStyleSheet("background-color: #F0E6FF; border-radius: 5px;")

        self.chars_layout = QVBoxLayout(self.chars_frame)

        self.chars_label = QLabel("Characters Present")

        self.chars_label.setStyleSheet("font-weight: bold;")

        self.chars_layout.addWidget(self.chars_label)

        self.chars_content = QLabel("No characters present")

        self.chars_layout.addWidget(self.chars_content)

        self.layout.addWidget(self.chars_frame)



        self.layout.addStretch()



    def update_info(self, location, memory_system):

        """Update widget with location information."""

        if not location:

            self.name_label.setText("No Location Selected")

            self.description.setText("")

            self.features_content.setText("No features available")

            self.chars_content.setText("No characters present")

            return



        self.name_label.setText(location.name)

        self.description.setText(location.description)



        if hasattr(location, 'features') and location.features:

            features_text = ""

            for feature in location.features:

                features_text += f"• {feature}<br>"

            self.features_content.setText(features_text)

        else:

            self.features_content.setText("No features available")



        # Find characters at this location

        characters_at_location = []

        if memory_system:

            for character in memory_system.card_manager.cards_by_type.get("character", {}).values():

                if hasattr(character, "location") and character.location == location.id:

                    characters_at_location.append(character.name)



        if characters_at_location:

            chars_text = ""

            for char_name in characters_at_location:

                chars_text += f"• {char_name}<br>"

            self.chars_content.setText(chars_text)

        else:

            self.chars_content.setText("No characters present")





class LoadingScreen(QDialog):

    """Loading screen dialog with progress updates."""



    def __init__(self, parent=None):

        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)

        self.setWindowTitle("Loading")



        # Set up the UI

        layout = QVBoxLayout(self)



        # Loading label

        self.label = QLabel("Loading AI Narrative RPG...")

        self.label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A5ACD;")

        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)



        # Progress message

        self.progress_label = QLabel("Initializing...")

        self.progress_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.progress_label)



        # Progress bar (cosmetic)

        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.progress_bar.setStyleSheet("""

            QProgressBar {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                text-align: center;

                background-color: #F0F0F0;

            }

            QProgressBar::chunk {

                background-color: #9370DB;

            }

        """)

        layout.addWidget(self.progress_bar)



        self.setFixedSize(400, 150)

        self.setStyleSheet("background-color: white;")



    def update_progress(self, message):

        """Update progress message."""

        self.progress_label.setText(message)





class OllamaHelper:

    """Helper class to interact with Ollama."""



    @staticmethod

    def is_installed():

        """Check if Ollama is installed."""

        try:

            # Try to execute 'ollama -h' to check if ollama is in PATH

            subprocess.run(

                ['ollama', '-h'],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                check=False

            )

            return True

        except FileNotFoundError:

            return False



    @staticmethod

    def is_running():

        """Check if Ollama server is running."""

        try:

            import requests

            response = requests.get("http://localhost:11434/api/tags", timeout=2)

            return response.status_code == 200

        except:

            return False



    @staticmethod

    def get_available_models():

        """Get list of available models in Ollama."""

        try:

            import requests

            response = requests.get("http://localhost:11434/api/tags")

            if response.status_code == 200:

                models = response.json().get('models', [])

                return models

            return []

        except:

            return []



    @staticmethod

    def install_model(model_name):

        """Install a model with Ollama."""

        try:

            subprocess.Popen(

                ['ollama', 'pull', model_name],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE

            )

            return True

        except:

            return False





class ModelSelectionDialog(QDialog):

    """Dialog for selecting the model to use."""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Select Model")

        self.setFixedWidth(500)



        layout = QVBoxLayout(self)



        # Title label

        title = QLabel("Select AI Model")

        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A5ACD;")

        layout.addWidget(title)



        # Model selection tabs

        self.tabs = QTabWidget()

        self.tabs.setStyleSheet("""

            QTabWidget::pane {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

            }

            QTabBar::tab {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-bottom-color: #CCCCCC;

                border-top-left-radius: 4px;

                border-top-right-radius: 4px;

                padding: 6px 10px;

            }

            QTabBar::tab:selected, QTabBar::tab:hover {

                background-color: #D8BFD8;

            }

            QTabBar::tab:selected {

                border-bottom-color: #D8BFD8;

            }

        """)



        # Ollama tab (first for emphasis)

        ollama_tab = QWidget()

        ollama_layout = QVBoxLayout(ollama_tab)



        # Check if Ollama is installed

        ollama_installed = OllamaHelper.is_installed()



        if ollama_installed:

            # Check if Ollama is running

            ollama_running = OllamaHelper.is_running()



            if ollama_running:

                # Get available models

                models = OllamaHelper.get_available_models()



                if models:

                    self.ollama_model_combo = QComboBox()

                    for model in models:

                        model_name = model.get('name', '')

                        if model_name:

                            size_mb = model.get('size', 0) / (1024 * 1024)

                            self.ollama_model_combo.addItem(f"{model_name} ({size_mb:.1f} MB)", model_name)



                    ollama_layout.addWidget(QLabel("Select an Ollama model:"))

                    ollama_layout.addWidget(self.ollama_model_combo)

                else:

                    no_models_label = QLabel("No models found in Ollama")

                    ollama_layout.addWidget(no_models_label)



                    # Button to download model

                    download_btn = QPushButton("Download a Model")

                    download_btn.clicked.connect(self.download_ollama_model)

                    ollama_layout.addWidget(download_btn)

            else:

                not_running_label = QLabel("Ollama is installed but not running")

                not_running_label.setStyleSheet("color: #FF5555;")

                ollama_layout.addWidget(not_running_label)



                instructions = QLabel(

                    "Please start Ollama by:\n"

                    "1. Opening a new terminal/command prompt\n"

                    "2. Running the command: ollama serve\n"

                    "3. Leaving that terminal open\n"

                    "4. Restart this application"

                )

                instructions.setWordWrap(True)

                ollama_layout.addWidget(instructions)

        else:

            not_installed_label = QLabel("Ollama is not installed")

            not_installed_label.setStyleSheet("color: #FF5555;")

            ollama_layout.addWidget(not_installed_label)



            instructions = QLabel(

                "To use Ollama (recommended free option):\n"

                "1. Download and install Ollama from https://ollama.ai\n"

                "2. Restart this application\n"

                "3. Use this tab to download models"

            )

            instructions.setWordWrap(True)

            ollama_layout.addWidget(instructions)



            # Button to open Ollama website

            website_btn = QPushButton("Go to Ollama Website")

            website_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://ollama.ai")))

            ollama_layout.addWidget(website_btn)



        ollama_layout.addStretch()

        self.tabs.addTab(ollama_tab, "Ollama (Free)")



        # Local models tab

        local_tab = QWidget()

        local_layout = QVBoxLayout(local_tab)



        local_models = self.list_local_models()



        if local_models:

            self.local_model_combo = QComboBox()

            for name, path, size, category in local_models:

                self.local_model_combo.addItem(f"{name} ({size:.1f} MB) - {category}", path)

            local_layout.addWidget(QLabel("Select a local GGUF model:"))

            local_layout.addWidget(self.local_model_combo)

        else:

            no_models_label = QLabel("No local models found in assets/models directory")

            no_models_label.setWordWrap(True)

            local_layout.addWidget(no_models_label)



            # Add instructions for getting models

            instructions = QLabel(

                "To use local models:\n"

                "1. Download GGUF models from Hugging Face\n"

                "2. Place them in the 'assets/models' folder\n"

                "3. Restart the application"

            )

            instructions.setStyleSheet("color: #555555;")

            instructions.setWordWrap(True)

            local_layout.addWidget(instructions)



        local_layout.addStretch()

        self.tabs.addTab(local_tab, "Local Models")



        # API models tab

        api_tab = QWidget()

        api_layout = QVBoxLayout(api_tab)



        # Get free models from config.py

        try:

            from config import FREE_MODELS

            free_models = FREE_MODELS if 'FREE_MODELS' in locals() else {}

        except ImportError:

            free_models = {}



        if free_models:

            self.api_model_combo = QComboBox()

            for name, info in free_models.items():

                desc = info.get("description", "")

                self.api_model_combo.addItem(f"{name} - {desc}", name)



            api_layout.addWidget(QLabel("Select an API model:"))

            api_layout.addWidget(self.api_model_combo)



            # API key input - REQUIRED now

            key_layout = QHBoxLayout()

            key_layout.addWidget(QLabel("API Key (required):"))

            self.api_key_input = QLineEdit()

            self.api_key_input.setPlaceholderText("Enter your API key (required for Together.ai)")

            key_layout.addWidget(self.api_key_input)

            api_layout.addLayout(key_layout)



            # Warning about API keys

            api_note = QLabel("Note: API models now require a valid API key from Together.ai")

            api_note.setStyleSheet("color: #FF5555; font-style: italic;")

            api_layout.addWidget(api_note)



            # Get API key link

            api_key_link = QPushButton("Get an API Key from Together.ai")

            api_key_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.together.ai/get-started")))

            api_layout.addWidget(api_key_link)

        else:

            no_apis = QLabel("No API models configured")

            api_layout.addWidget(no_apis)



        api_layout.addStretch()

        self.tabs.addTab(api_tab, "API Models")



        layout.addWidget(self.tabs)



        # Default option

        default_btn = QPushButton("Use Default Model (from config.py)")

        default_btn.setStyleSheet("""

            QPushButton {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-radius: 4px;

                padding: 6px;

            }

            QPushButton:hover {

                background-color: #D8BFD8;

            }

        """)

        default_btn.clicked.connect(self.use_default)

        layout.addWidget(default_btn)



        # Buttons

        btn_layout = QHBoxLayout()



        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)



        select_btn = QPushButton("Select")

        select_btn.setStyleSheet("""

            QPushButton {

                background-color: #9370DB;

                color: white;

                border: none;

                border-radius: 4px;

                padding: 6px;

            }

            QPushButton:hover {

                background-color: #8A2BE2;

            }

        """)

        select_btn.clicked.connect(self.accept)



        btn_layout.addWidget(cancel_btn)

        btn_layout.addWidget(select_btn)



        layout.addLayout(btn_layout)



        # Store the selection

        self.selection = None



    def download_ollama_model(self):

        """Download a model using Ollama."""

        # List of recommended models

        recommended_models = [

            "llama3",

            "mistral",

            "phi",

            "llama2",

            "codellama",

            "gemma",

            "orca-mini"

        ]



        # Show dialog to select model

        model, ok = QInputDialog.getItem(

            self, "Download Ollama Model",

            "Select a model to download:",

            recommended_models, 0, False

        )



        if ok and model:

            # Show progress dialog

            progress_dialog = QMessageBox(self)

            progress_dialog.setWindowTitle("Downloading Model")

            progress_dialog.setText(

                f"Starting download of {model}...\n\nThis will continue in the background.\nYou can close this dialog and check Ollama status later.")

            progress_dialog.setStandardButtons(QMessageBox.Ok)



            # Start download process

            success = OllamaHelper.install_model(model)



            if not success:

                QMessageBox.warning(self, "Download Error",

                                    "Failed to start the download. Make sure Ollama is running.")



    def list_local_models(self):

        """List GGUF models in assets/models directory."""

        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")



        if not os.path.exists(models_dir):

            os.makedirs(models_dir, exist_ok=True)

            return []



        models = []

        for file in os.listdir(models_dir):

            if file.lower().endswith('.gguf'):

                model_path = os.path.join(models_dir, file)

                size_mb = os.path.getsize(model_path) / (1024 * 1024)



                # Add model size category for user-friendly display

                if size_mb < 2000:

                    size_category = "Small (Fast)"

                elif size_mb < 5000:

                    size_category = "Medium"

                elif size_mb < 15000:

                    size_category = "Large"

                else:

                    size_category = "Very Large (Slow)"



                models.append((file, f"assets/models/{file}", size_mb, size_category))



        # Sort models by size (smallest first) for better UX

        models.sort(key=lambda x: x[2])

        return models



    def get_selection(self):

        """Get the selected model configuration."""

        if self.selection == "default":

            return {"type": "default"}



        current_tab = self.tabs.currentIndex()



        if current_tab == 0:  # Ollama tab

            if hasattr(self, 'ollama_model_combo') and self.ollama_model_combo.count() > 0:

                selected_model = self.ollama_model_combo.currentData()

                return {"type": "ollama", "name": selected_model}

        elif current_tab == 1:  # Local models tab

            if hasattr(self, 'local_model_combo') and self.local_model_combo.count() > 0:

                selected_path = self.local_model_combo.currentData()

                return {"type": "local", "path": selected_path}

        elif current_tab == 2:  # API models tab

            if hasattr(self, 'api_model_combo') and self.api_model_combo.count() > 0:

                selected_model = self.api_model_combo.currentData()

                api_key = self.api_key_input.text() if hasattr(self, 'api_key_input') else ""



                # Validate API key for Together.ai

                if not api_key:

                    QMessageBox.warning(self, "API Key Required",

                                        "Together.ai API models now require an API key. Please enter a valid API key.")

                    return None



                return {"type": "free", "name": selected_model, "api_key": api_key}



        # If no valid selection, return default

        return {"type": "default"}



    def use_default(self):

        """Use default model from config.py."""

        self.selection = "default"

        self.accept()



    def accept(self):

        """Override accept to store selection."""

        if not self.selection:  # If not already set by use_default

            self.selection = self.get_selection()



            # If selection is None (invalid), don't accept the dialog

            if self.selection is None:

                return



        super().accept()





class CampaignSelectionDialog(QDialog):

    """Dialog for selecting or creating a campaign."""



    def __init__(self, memory_system, parent=None):

        super().__init__(parent)

        self.memory_system = memory_system

        self.setWindowTitle("Select Campaign")

        self.resize(500, 400)



        layout = QVBoxLayout(self)



        # Title label

        title = QLabel("Select Campaign")

        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A5ACD;")

        layout.addWidget(title)



        # Campaign list

        self.campaign_list = QListWidget()

        self.campaign_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 8px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Load available campaigns

        self.campaigns = self.memory_system.get_available_campaigns()



        for campaign in self.campaigns:

            campaign_name = campaign.get("name", "Unknown Campaign")

            created_date = time.strftime("%Y-%m-%d", time.localtime(campaign.get("created", 0)))

            modified_date = time.strftime("%Y-%m-%d", time.localtime(campaign.get("last_modified", 0)))



            item = QListWidgetItem(f"{campaign_name} (Created: {created_date}, Last played: {modified_date})")

            self.campaign_list.addItem(item)



        layout.addWidget(self.campaign_list)



        # New campaign button

        new_campaign_btn = QPushButton("Create New Campaign")

        new_campaign_btn.setStyleSheet("""

            QPushButton {

                background-color: #9370DB;

                color: white;

                border: none;

                border-radius: 4px;

                padding: 8px;

                font-weight: bold;

            }

            QPushButton:hover {

                background-color: #8A2BE2;

            }

        """)

        new_campaign_btn.clicked.connect(self.create_new_campaign)

        layout.addWidget(new_campaign_btn)



        # Buttons

        btn_layout = QHBoxLayout()



        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)



        select_btn = QPushButton("Select")

        select_btn.setStyleSheet("""

            QPushButton {

                background-color: #9370DB;

                color: white;

                border: none;

                border-radius: 4px;

                padding: 6px;

            }

            QPushButton:hover {

                background-color: #8A2BE2;

            }

        """)

        select_btn.clicked.connect(self.accept)



        btn_layout.addWidget(cancel_btn)

        btn_layout.addWidget(select_btn)



        layout.addLayout(btn_layout)



        # Track selected campaign

        self.selected_campaign_id = None

        self.campaign_list.itemClicked.connect(self.campaign_selected)



    def campaign_selected(self, item):

        """Handle campaign selection."""

        idx = self.campaign_list.row(item)

        if 0 <= idx < len(self.campaigns):

            self.selected_campaign_id = self.campaigns[idx].get("id")

    def create_new_campaign(self):
        """Signal that a new campaign should be created."""
        # Get campaign name
        name, ok = QInputDialog.getText(self, "New Campaign", "Enter campaign name:")
        if not ok or not name:
            return

        # Just store the name and set a flag - don't try to create the campaign here
        self.new_campaign_name = name
        self.new_campaign_requested = True
        self.accept()  # Close dialog with "accepted" result



    def accept(self):

        """Override accept to validate selection."""

        if not self.selected_campaign_id and self.campaigns:

            # If nothing selected but campaigns exist, select the first one

            self.selected_campaign_id = self.campaigns[0].get("id")



        if self.selected_campaign_id:

            super().accept()

        else:

            QMessageBox.warning(self, "No Campaign Selected",

                                "Please select a campaign or create a new one.")





from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl

from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor, QIcon, QDesktopServices

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLineEdit,

                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget,

                             QLabel, QComboBox, QTabWidget, QSplitter,

                             QListWidget, QListWidgetItem, QScrollArea,

                             QFrame, QDialog, QMessageBox, QProgressBar,

                             QInputDialog, QCheckBox, QSlider, QSizePolicy)

import requests

import sys

import os

import json

import subprocess

import time



# Import from the main RPG system

from memory_system import MemorySystem

from llm_interface import LLMInterface

from config import CAMPAIGNS_DIR, FREE_MODELS





class CharacterDialog(QDialog):

    """Dialog for creating or editing a character."""



    def __init__(self, memory_system, character=None, parent=None):

        super().__init__(parent)

        self.memory_system = memory_system

        self.character = character

        self.is_edit_mode = character is not None



        self.setWindowTitle("Create Character" if not self.is_edit_mode else "Edit Character")

        self.resize(400, 600)

        self.setup_ui()



        # If editing, populate fields

        if self.is_edit_mode:

            self.populate_fields()



    def setup_ui(self):

        """Set up the main user interface."""

        # Set up menu bar first

        self.setup_menu_bar()



        # Create the main widget and layout

        main_widget = QWidget()



        # Change to use a vertical QSplitter as the main container instead of QVBoxLayout

        main_splitter = QSplitter(Qt.Vertical)

        main_splitter.setChildrenCollapsible(False)

        main_splitter.setHandleWidth(8)  # Make handles easier to grab

        main_splitter.setOpaqueResize(True)



        # Create header widget to contain campaign name and typing speed

        header_widget = QWidget()

        header_layout = QVBoxLayout(header_widget)

        header_layout.setContentsMargins(10, 5, 10, 5)



        # Create the game header

        header = QLabel(f"Campaign: {self.memory_system.campaign_name}")

        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #6A5ACD; padding: 8px;")

        header_layout.addWidget(header)



        # Create a simplified typing speed control

        speed_layout = QHBoxLayout()

        speed_layout.setContentsMargins(0, 0, 0, 0)



        # Slider label with better styling

        typing_speed_label = QLabel("Typing Speed:")

        typing_speed_label.setStyleSheet("font-weight: bold;")

        speed_layout.addWidget(typing_speed_label)



        # Create an improved slider with REVERSED direction (slow to fast)

        self.typing_speed_slider = QSlider(Qt.Horizontal)

        self.typing_speed_slider.setMinimum(1)  # Now this is SLOW (100ms)

        self.typing_speed_slider.setMaximum(100)  # Now this is FAST (1ms)

        self.typing_speed_slider.setValue(70)  # Default value

        self.typing_speed_slider.setTickPosition(QSlider.TicksBelow)

        self.typing_speed_slider.setTickInterval(10)

        self.typing_speed_slider.setStyleSheet("""

            QSlider::groove:horizontal {

                border: 1px solid #999999;

                height: 8px;

                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 

                                          stop:0 #B592E5, stop:1 #D8BFD8);

                border-radius: 4px;

            }



            QSlider::handle:horizontal {

                background: #9370DB;

                border: 1px solid #5E5E5E;

                width: 18px;

                margin: -5px 0;

                border-radius: 9px;

            }



            QSlider::handle:horizontal:hover {

                background: #8A2BE2;

            }



            QSlider::sub-page:horizontal {

                background: #9370DB;

                border-radius: 4px;

            }



            QSlider::add-page:horizontal {

                background: #E6E6FA;

                border-radius: 4px;

            }



            QSlider::tick-mark:horizontal {

                background: #777777;

                width: 1px;

                height: 3px;

                margin-top: 2px;

            }

        """)

        speed_layout.addWidget(self.typing_speed_slider)

        header_layout.addLayout(speed_layout)



        # Add header to main splitter

        main_splitter.addWidget(header_widget)



        # Create the content splitter (horizontal split between game area and sidebar)

        content_splitter = QSplitter(Qt.Horizontal)

        content_splitter.setChildrenCollapsible(False)

        content_splitter.setHandleWidth(8)

        content_splitter.setOpaqueResize(True)



        # Add the content splitter to the main splitter

        main_splitter.addWidget(content_splitter)



        # Set the main splitter as the central widget

        self.setCentralWidget(main_splitter)



        # Set main splitter sizes (header gets minimal space, content gets the rest)

        main_splitter.setSizes([100, 900])  # Header gets 10%, content gets 90%



        # Create the game vertical splitter

        game_vertical_splitter = QSplitter(Qt.Vertical)

        game_vertical_splitter.setChildrenCollapsible(False)

        game_vertical_splitter.setHandleWidth(8)

        game_vertical_splitter.setOpaqueResize(True)



        # Game display area

        self.game_display = QTextEdit()

        self.game_display.setReadOnly(True)

        self.game_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.game_display.setStyleSheet("""

            background-color: #FFFFFF;

            border: 1px solid #CCCCCC;

            border-radius: 5px;

            padding: 10px;

        """)



        # Set a nicer font

        game_font = QFont("Roboto", 11)

        self.game_display.setFont(game_font)



        game_vertical_splitter.addWidget(self.game_display)



        # User input area

        input_widget = QWidget()

        input_layout = QHBoxLayout(input_widget)

        input_layout.setContentsMargins(0, 5, 0, 0)



        self.user_input = QLineEdit()

        self.user_input.setPlaceholderText("Enter your action or dialogue...")

        self.user_input.setStyleSheet("""

            background-color: #FFFFFF;

            border: 1px solid #CCCCCC;

            border-radius: 5px;

            padding: 8px;

        """)

        self.user_input.returnPressed.connect(self.process_input)



        self.send_button = QPushButton("Send")

        self.send_button.setStyleSheet("""

            QPushButton {

                background-color: #9370DB;

                color: white;

                border: none;

                border-radius: 5px;

                padding: 8px 12px;

            }

            QPushButton:hover {

                background-color: #8A2BE2;

            }

        """)

        self.send_button.clicked.connect(self.process_input)



        # Add "Save Campaign" button

        save_campaign_btn = QPushButton("Save Campaign")

        save_campaign_btn.clicked.connect(self.save_campaign)

        save_campaign_btn.setStyleSheet("""

            QPushButton {

                background-color: #90EE90;

                border: none;

                border-radius: 5px;

                padding: 8px 12px;

            }

            QPushButton:hover {

                background-color: #7CCD7C;

            }

        """)



        input_layout.addWidget(self.user_input)

        input_layout.addWidget(self.send_button)

        input_layout.addWidget(save_campaign_btn)



        game_vertical_splitter.addWidget(input_widget)

        game_vertical_splitter.setSizes([800, 100])  # Text area gets 80%, input gets 20%



        # Add the game splitter to the content splitter

        content_splitter.addWidget(game_vertical_splitter)



        # Sidebar for game state

        sidebar = QTabWidget()

        sidebar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        sidebar.setStyleSheet("""

            QTabWidget::pane {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

            }

            QTabBar::tab {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-bottom-color: #CCCCCC;

                border-top-left-radius: 4px;

                border-top-right-radius: 4px;

                padding: 6px 10px;

            }

            QTabBar::tab:selected, QTabBar::tab:hover {

                background-color: #D8BFD8;

            }

            QTabBar::tab:selected {

                border-bottom-color: #D8BFD8;

            }

        """)



        # Characters tab

        characters_tab = QWidget()

        characters_layout = QVBoxLayout(characters_tab)



        # Characters list

        self.characters_list = QListWidget()

        self.characters_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.characters_list.setMinimumHeight(100)

        self.characters_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Character info panel

        self.character_info = CharacterInfoWidget()

        self.character_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.character_info.setMinimumHeight(200)



        # Add "Add New Character" button

        add_character_btn = QPushButton("+ Add Character")

        add_character_btn.clicked.connect(self.create_character)

        add_character_btn.setStyleSheet("""

            QPushButton {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-radius: 4px;

                padding: 6px;

                font-weight: bold;

            }

            QPushButton:hover {

                background-color: #D8BFD8;

            }

        """)



        # Split the tab into list and details

        char_splitter = QSplitter(Qt.Vertical)

        char_splitter.setChildrenCollapsible(False)  # Prevent sections from collapsing completely

        char_splitter.setHandleWidth(8)  # Make handles easier to grab

        char_splitter.setOpaqueResize(True)  # Resize in real-time for better UX

        char_splitter.addWidget(self.characters_list)

        char_splitter.addWidget(self.character_info)



        # Set stretch factors for better resizing behavior

        char_splitter.setStretchFactor(0, 1)  # Character list gets 1 part

        char_splitter.setStretchFactor(1, 2)  # Character details get 2 parts



        characters_layout.addWidget(char_splitter)

        characters_layout.addWidget(add_character_btn)

        sidebar.addTab(characters_tab, "Characters")



        # Locations tab

        locations_tab = QWidget()

        locations_layout = QVBoxLayout(locations_tab)



        # Locations list

        self.locations_list = QListWidget()

        self.locations_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.locations_list.setMinimumHeight(100)

        self.locations_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Location info panel

        self.location_info = LocationInfoWidget()

        self.location_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.location_info.setMinimumHeight(200)



        # Add "Add New Location" button

        add_location_btn = QPushButton("+ Add Location")

        add_location_btn.clicked.connect(self.create_location)

        add_location_btn.setStyleSheet("""

            QPushButton {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-radius: 4px;

                padding: 6px;

                font-weight: bold;

            }

            QPushButton:hover {

                background-color: #D8BFD8;

            }

        """)



        # Split the tab into list and details

        loc_splitter = QSplitter(Qt.Vertical)

        loc_splitter.setChildrenCollapsible(False)  # Prevent sections from collapsing completely

        loc_splitter.setHandleWidth(8)  # Make handles easier to grab

        loc_splitter.setOpaqueResize(True)  # Resize in real-time for better UX

        loc_splitter.addWidget(self.locations_list)

        loc_splitter.addWidget(self.location_info)



        # Set stretch factors for better resizing behavior

        loc_splitter.setStretchFactor(0, 1)  # Location list gets 1 part

        loc_splitter.setStretchFactor(1, 2)  # Location details get 2 parts



        locations_layout.addWidget(loc_splitter)

        locations_layout.addWidget(add_location_btn)

        sidebar.addTab(locations_tab, "Locations")



        # Items tab

        items_tab = QWidget()

        items_layout = QVBoxLayout(items_tab)



        # Items list

        self.items_list = QListWidget()

        self.items_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.items_list.setMinimumHeight(150)

        self.items_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Add "Add New Item" button

        add_item_btn = QPushButton("+ Add Item")

        add_item_btn.clicked.connect(self.create_item)

        add_item_btn.setStyleSheet("""

            QPushButton {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-radius: 4px;

                padding: 6px;

                font-weight: bold;

            }

            QPushButton:hover {

                background-color: #D8BFD8;

            }

        """)



        items_layout.addWidget(self.items_list)

        items_layout.addWidget(add_item_btn)

        sidebar.addTab(items_tab, "Items")



        # Set up context menus for lists

        self.characters_list.setContextMenuPolicy(Qt.CustomContextMenu)

        self.characters_list.customContextMenuRequested.connect(self.show_characters_context_menu)



        self.locations_list.setContextMenuPolicy(Qt.CustomContextMenu)

        self.locations_list.customContextMenuRequested.connect(self.show_locations_context_menu)



        self.items_list.setContextMenuPolicy(Qt.CustomContextMenu)

        self.items_list.customContextMenuRequested.connect(self.show_items_context_menu)



        # Connect signals

        self.characters_list.currentItemChanged.connect(self.on_character_selected)

        self.locations_list.currentItemChanged.connect(self.on_location_selected)



        # Add sidebar to content splitter

        content_splitter.addWidget(sidebar)



        # Set initial content splitter sizes

        content_splitter.setSizes([700, 300])  # Game area gets 70%, sidebar gets 30%



        # Connect the slider to update the typing speed

        self.typing_speed_slider.valueChanged.connect(self.update_typing_speed_with_indicator)



        # Initialize game state

        self.update_game_state()



        # Display welcome message

        self.display_wel



    def add_trait_row(self):

        """Add a row for trait input."""

        trait_row = QHBoxLayout()



        trait_name = QLineEdit()

        trait_name.setPlaceholderText("Trait name")

        trait_row.addWidget(trait_name)



        trait_value = QLineEdit()

        trait_value.setPlaceholderText("Value")

        trait_row.addWidget(trait_value)



        remove_btn = QPushButton("X")

        remove_btn.setMaximumWidth(30)

        remove_btn.clicked.connect(lambda: self.remove_trait_row(trait_row))

        trait_row.addWidget(remove_btn)



        # Store the layout and widgets

        widget_index = len(self.traits)

        self.traits_layout.insertLayout(widget_index, trait_row)

        self.traits.append((trait_name, trait_value))



    def remove_trait_row(self, row_layout):

        """Remove a trait row."""

        # Find the row in the layout

        for i in range(self.traits_layout.count() - 1):  # -1 to skip the Add button

            if self.traits_layout.itemAt(i) == row_layout:

                # Remove widgets from layout

                while row_layout.count():

                    item = row_layout.takeAt(0)

                    widget = item.widget()

                    if widget:

                        widget.deleteLater()



                # Remove layout from parent

                self.traits_layout.removeItem(row_layout)



                # Remove from traits list

                if i < len(self.traits):

                    self.traits.pop(i)



                break



    def populate_locations(self):

        """Populate the locations dropdown."""

        # Add "None" option

        self.location_combo.addItem("None", None)



        # Add existing locations

        for loc_id, location in self.memory_system.card_manager.cards_by_type.get("location", {}).items():

            self.location_combo.addItem(location.name, loc_id)



    def populate_fields(self):

        """Populate fields with existing character data."""

        if not self.character:

            return



        self.name_input.setText(self.character.name)

        self.description_input.setText(self.character.description)



        # Populate traits (remove default one first)

        if len(self.traits) > 0:

            self.remove_trait_row(self.traits_layout.itemAt(0))

            self.traits = []



        if hasattr(self.character, "traits"):

            for name, value in self.character.traits.items():

                self.add_trait_row()

                self.traits[-1][0].setText(name)

                self.traits[-1][1].setText(str(value))



        # Populate inventory

        if hasattr(self.character, "inventory"):

            self.inventory_input.setText("\n".join(self.character.inventory))



        # Set location

        if hasattr(self.character, "location"):

            loc_id = self.character.location

            for i in range(self.location_combo.count()):

                if self.location_combo.itemData(i) == loc_id:

                    self.location_combo.setCurrentIndex(i)

                    break



        # Set status

        if hasattr(self.character, "status"):

            status = self.character.status

            index = self.status_combo.findText(status)

            if index >= 0:

                self.status_combo.setCurrentIndex(index)



    def get_character_data(self):

        """Get character data from form fields."""

        name = self.name_input.text()

        description = self.description_input.toPlainText()



        # Build traits dictionary

        traits = {}

        for trait_name, trait_value in self.traits:

            name_text = trait_name.text().strip()

            value_text = trait_value.text().strip()

            if name_text:

                traits[name_text] = value_text



        # Build inventory list

        inventory = [item.strip() for item in self.inventory_input.toPlainText().split("\n") if item.strip()]



        # Get location

        location = self.location_combo.currentData()



        # Get status

        status = self.status_combo.currentText()



        return {

            "name": name,

            "description": description,

            "traits": traits,

            "inventory": inventory,

            "location": location,

            "status": status

        }





class LocationDialog(QDialog):

    """Dialog for creating or editing a location."""



    def __init__(self, memory_system, location=None, parent=None):

        super().__init__(parent)

        self.memory_system = memory_system

        self.location = location

        self.is_edit_mode = location is not None



        self.setWindowTitle("Create Location" if not self.is_edit_mode else "Edit Location")

        self.resize(400, 600)

        self.setup_ui()



        # If editing, populate fields

        if self.is_edit_mode:

            self.populate_fields()



    def setup_ui(self):

        """Set up the dialog UI."""

        layout = QVBoxLayout(self)



        # Location name

        name_layout = QHBoxLayout()

        name_layout.addWidget(QLabel("Name:"))

        self.name_input = QLineEdit()

        name_layout.addWidget(self.name_input)

        layout.addLayout(name_layout)



        # Location description

        layout.addWidget(QLabel("Description:"))

        self.description_input = QTextEdit()

        self.description_input.setPlaceholderText("Enter location description...")

        layout.addWidget(self.description_input)



        # Location region

        region_layout = QHBoxLayout()

        region_layout.addWidget(QLabel("Region:"))

        self.region_input = QLineEdit()

        region_layout.addWidget(self.region_input)

        layout.addLayout(region_layout)



        # Location features

        layout.addWidget(QLabel("Features (one per line):"))

        self.features_input = QTextEdit()

        self.features_input.setPlaceholderText("Enter location features, one per line...")

        layout.addWidget(self.features_input)



        # Location atmosphere

        atmosphere_layout = QHBoxLayout()

        atmosphere_layout.addWidget(QLabel("Atmosphere:"))

        self.atmosphere_input = QLineEdit()

        atmosphere_layout.addWidget(self.atmosphere_input)

        layout.addLayout(atmosphere_layout)



        # Buttons

        btn_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)



        save_btn = QPushButton("Save")

        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(save_btn)



        layout.addLayout(btn_layout)



    def populate_fields(self):

        """Populate fields with existing location data."""

        if not self.location:

            return



        self.name_input.setText(self.location.name)

        self.description_input.setText(self.location.description)



        if hasattr(self.location, "region"):

            self.region_input.setText(self.location.region)



        if hasattr(self.location, "features"):

            self.features_input.setText("\n".join(self.location.features))



        if hasattr(self.location, "atmosphere"):

            self.atmosphere_input.setText(self.location.atmosphere)



    def get_location_data(self):

        """Get location data from form fields."""

        name = self.name_input.text()

        description = self.description_input.toPlainText()

        region = self.region_input.text()



        # Build features list

        features = [feature.strip() for feature in self.features_input.toPlainText().split("\n") if feature.strip()]



        atmosphere = self.atmosphere_input.text()



        return {

            "name": name,

            "description": description,

            "region": region,

            "features": features,

            "atmosphere": atmosphere

        }





class ItemDialog(QDialog):

    """Dialog for creating or editing an item."""



    def __init__(self, memory_system, item=None, parent=None):

        super().__init__(parent)

        self.memory_system = memory_system

        self.item = item

        self.is_edit_mode = item is not None



        self.setWindowTitle("Create Item" if not self.is_edit_mode else "Edit Item")

        self.resize(400, 500)

        self.setup_ui()



        # If editing, populate fields

        if self.is_edit_mode:

            self.populate_fields()



    def setup_ui(self):

        """Set up the dialog UI."""

        layout = QVBoxLayout(self)



        # Item name

        name_layout = QHBoxLayout()

        name_layout.addWidget(QLabel("Name:"))

        self.name_input = QLineEdit()

        name_layout.addWidget(self.name_input)

        layout.addLayout(name_layout)



        # Item description

        layout.addWidget(QLabel("Description:"))

        self.description_input = QTextEdit()

        self.description_input.setPlaceholderText("Enter item description...")

        layout.addWidget(self.description_input)



        # Item properties

        layout.addWidget(QLabel("Properties:"))

        self.props_widget = QWidget()

        self.props_layout = QVBoxLayout(self.props_widget)

        self.properties = []  # List to store property rows (name, value)



        # Add initial property row

        self.add_property_row()



        # Add button for adding more properties

        add_prop_btn = QPushButton("Add Property")

        add_prop_btn.clicked.connect(self.add_property_row)

        self.props_layout.addWidget(add_prop_btn)



        # Add properties widget to scroll area

        props_scroll = QScrollArea()

        props_scroll.setWidgetResizable(True)

        props_scroll.setWidget(self.props_widget)

        layout.addWidget(props_scroll)



        # Item owner

        owner_layout = QHBoxLayout()

        owner_layout.addWidget(QLabel("Owner:"))

        self.owner_combo = QComboBox()

        self.populate_owners()

        owner_layout.addWidget(self.owner_combo)

        layout.addLayout(owner_layout)



        # Item location

        location_layout = QHBoxLayout()

        location_layout.addWidget(QLabel("Location:"))

        self.location_combo = QComboBox()

        self.populate_locations()

        location_layout.addWidget(self.location_combo)

        layout.addLayout(location_layout)



        # Buttons

        btn_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)



        save_btn = QPushButton("Save")

        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(save_btn)



        layout.addLayout(btn_layout)



    def add_property_row(self):

        """Add a row for property input."""

        prop_row = QHBoxLayout()



        prop_name = QLineEdit()

        prop_name.setPlaceholderText("Property name")

        prop_row.addWidget(prop_name)



        prop_value = QLineEdit()

        prop_value.setPlaceholderText("Value")

        prop_row.addWidget(prop_value)



        remove_btn = QPushButton("X")

        remove_btn.setMaximumWidth(30)

        remove_btn.clicked.connect(lambda: self.remove_property_row(prop_row))

        prop_row.addWidget(remove_btn)



        # Store the layout and widgets

        widget_index = len(self.properties)

        self.props_layout.insertLayout(widget_index, prop_row)

        self.properties.append((prop_name, prop_value))



    def remove_property_row(self, row_layout):

        """Remove a property row."""

        # Find the row in the layout

        for i in range(self.props_layout.count() - 1):  # -1 to skip the Add button

            if self.props_layout.itemAt(i) == row_layout:

                # Remove widgets from layout

                while row_layout.count():

                    item = row_layout.takeAt(0)

                    widget = item.widget()

                    if widget:

                        widget.deleteLater()



                # Remove layout from parent

                self.props_layout.removeItem(row_layout)



                # Remove from properties list

                if i < len(self.properties):

                    self.properties.pop(i)



                break



    def populate_owners(self):

        """Populate the owners dropdown."""

        # Add "None" option

        self.owner_combo.addItem("None", None)



        # Add existing characters

        for char_id, character in self.memory_system.card_manager.cards_by_type.get("character", {}).items():

            self.owner_combo.addItem(character.name, char_id)



    def populate_locations(self):

        """Populate the locations dropdown."""

        # Add "None" option

        self.location_combo.addItem("None", None)



        # Add existing locations

        for loc_id, location in self.memory_system.card_manager.cards_by_type.get("location", {}).items():

            self.location_combo.addItem(location.name, loc_id)



    def populate_fields(self):

        """Populate fields with existing item data."""

        if not self.item:

            return



        self.name_input.setText(self.item.name)

        self.description_input.setText(self.item.description)



        # Populate properties (remove default one first)

        if len(self.properties) > 0:

            self.remove_property_row(self.props_layout.itemAt(0))

            self.properties = []



        if hasattr(self.item, "properties"):

            for name, value in self.item.properties.items():

                self.add_property_row()

                self.properties[-1][0].setText(name)

                self.properties[-1][1].setText(str(value))



        # Set owner

        if hasattr(self.item, "owner"):

            owner_id = self.item.owner

            for i in range(self.owner_combo.count()):

                if self.owner_combo.itemData(i) == owner_id:

                    self.owner_combo.setCurrentIndex(i)

                    break



        # Set location

        if hasattr(self.item, "location"):

            loc_id = self.item.location

            for i in range(self.location_combo.count()):

                if self.location_combo.itemData(i) == loc_id:

                    self.location_combo.setCurrentIndex(i)

                    break



    def get_item_data(self):

        """Get item data from form fields."""

        name = self.name_input.text()

        description = self.description_input.toPlainText()



        # Build properties dictionary

        properties = {}

        for prop_name, prop_value in self.properties:

            name_text = prop_name.text().strip()

            value_text = prop_value.text().strip()

            if name_text:

                properties[name_text] = value_text



        # Get owner

        owner = self.owner_combo.currentData()



        # Get location

        location = self.location_combo.currentData()



        return {

            "name": name,

            "description": description,

            "properties": properties,

            "owner": owner,

            "location": location

        }





class StoryDialog(QDialog):

    """Dialog for creating or editing a story."""



    def __init__(self, memory_system, story=None, parent=None):

        super().__init__(parent)

        self.memory_system = memory_system

        self.story = story

        self.is_edit_mode = story is not None



        self.setWindowTitle("Create Story" if not self.is_edit_mode else "Edit Story")

        self.resize(400, 600)

        self.setup_ui()



        # If editing, populate fields

        if self.is_edit_mode:

            self.populate_fields()



    def setup_ui(self):

        """Set up the dialog UI."""

        layout = QVBoxLayout(self)



        # Story name

        name_layout = QHBoxLayout()

        name_layout.addWidget(QLabel("Name:"))

        self.name_input = QLineEdit()

        name_layout.addWidget(self.name_input)

        layout.addLayout(name_layout)



        # Story description

        layout.addWidget(QLabel("Description:"))

        self.description_input = QTextEdit()

        self.description_input.setPlaceholderText("Enter story description...")

        layout.addWidget(self.description_input)



        # Story type

        type_layout = QHBoxLayout()

        type_layout.addWidget(QLabel("Type:"))

        self.type_combo = QComboBox()

        self.type_combo.addItems(["main", "side", "character", "quest"])

        type_layout.addWidget(self.type_combo)

        layout.addLayout(type_layout)



        # Story status

        status_layout = QHBoxLayout()

        status_layout.addWidget(QLabel("Status:"))

        self.status_combo = QComboBox()

        self.status_combo.addItems(["active", "completed", "failed"])

        status_layout.addWidget(self.status_combo)

        layout.addLayout(status_layout)



        # Involved characters

        layout.addWidget(QLabel("Involved Characters:"))

        self.characters_list = QListWidget()

        self.populate_characters_list()

        layout.addWidget(self.characters_list)



        # Involved locations

        layout.addWidget(QLabel("Involved Locations:"))

        self.locations_list = QListWidget()

        self.populate_locations_list()

        layout.addWidget(self.locations_list)



        # Buttons

        btn_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)



        save_btn = QPushButton("Save")

        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(save_btn)



        layout.addLayout(btn_layout)



    def populate_characters_list(self):

        """Populate the characters list."""

        self.characters_list.clear()

        self.characters_list.setSelectionMode(QListWidget.MultiSelection)



        for char_id, character in self.memory_system.card_manager.cards_by_type.get("character", {}).items():

            item = QListWidgetItem(character.name)

            item.setData(Qt.UserRole, char_id)

            self.characters_list.addItem(item)



    def populate_locations_list(self):

        """Populate the locations list."""

        self.locations_list.clear()

        self.locations_list.setSelectionMode(QListWidget.MultiSelection)



        for loc_id, location in self.memory_system.card_manager.cards_by_type.get("location", {}).items():

            item = QListWidgetItem(location.name)

            item.setData(Qt.UserRole, loc_id)

            self.locations_list.addItem(item)



    def populate_fields(self):

        """Populate fields with existing story data."""

        if not self.story:

            return



        self.name_input.setText(self.story.name)

        self.description_input.setText(self.story.description)



        # Set type

        if hasattr(self.story, "plot_type"):

            index = self.type_combo.findText(self.story.plot_type)

            if index >= 0:

                self.type_combo.setCurrentIndex(index)



        # Set status

        if hasattr(self.story, "status"):

            index = self.status_combo.findText(self.story.status)

            if index >= 0:

                self.status_combo.setCurrentIndex(index)



        # Select involved characters

        if hasattr(self.story, "involved_characters"):

            for i in range(self.characters_list.count()):

                item = self.characters_list.item(i)

                if item.data(Qt.UserRole) in self.story.involved_characters:

                    item.setSelected(True)



        # Select involved locations

        if hasattr(self.story, "involved_locations"):

            for i in range(self.locations_list.count()):

                item = self.locations_list.item(i)

                if item.data(Qt.UserRole) in self.story.involved_locations:

                    item.setSelected(True)



    def get_story_data(self):

        """Get story data from form fields."""

        name = self.name_input.text()

        description = self.description_input.toPlainText()

        plot_type = self.type_combo.currentText()

        status = self.status_combo.currentText()



        # Get involved characters

        involved_characters = []

        for i in range(self.characters_list.count()):

            item = self.characters_list.item(i)

            if item.isSelected():

                involved_characters.append(item.data(Qt.UserRole))



        # Get involved locations

        involved_locations = []

        for i in range(self.locations_list.count()):

            item = self.locations_list.item(i)

            if item.isSelected():

                involved_locations.append(item.data(Qt.UserRole))



        return {

            "name": name,

            "description": description,

            "plot_type": plot_type,

            "status": status,

            "involved_characters": involved_characters,

            "involved_locations": involved_locations

        }





class RpgNarrativeGUI(QMainWindow):

    """Main GUI window for the AI Narrative RPG system."""



    def __init__(self):

        super().__init__()

        self.setWindowTitle("AI Narrative RPG System")

        self.resize(1000, 700)



        # Set the lavender theme

        self.set_lavender_theme()



        # Initialize model and system

        self.memory_system = None

        self.initialize_model()



        # Other initializations

        self.current_response = ""

        self.current_position = 0

        self.typing_in_progress = False

        self.typing_timer = None



        # Default typing speed (ms between characters)

        self.typing_speed = 30



    def initialize_model(self):

        """Initialize the model selection and loading process."""

        # Show model selection dialog

        model_dialog = ModelSelectionDialog(self)

        if model_dialog.exec_() == QDialog.Accepted:

            # Get selected model

            model_selection = model_dialog.selection



            # Show loading screen

            self.loading_screen = LoadingScreen(self)

            self.loading_screen.show()



            # Initialize model and memory system in separate thread

            self.loading_thread = ModelLoadingThread(model_selection)

            self.loading_thread.progress.connect(self.loading_screen.update_progress)

            self.loading_thread.finished.connect(self.on_system_initialized)

            self.loading_thread.error.connect(self.on_initialization_error)

            self.loading_thread.start()

        else:

            # User canceled

            sys.exit()

    def on_system_initialized(self, memory_system):
        """Called when the system is initialized."""
        self.memory_system = memory_system
        self.loading_screen.close()

        # Repair all campaigns before showing selection dialog
        self.repair_all_campaigns()

        # Now show campaign selection
        self.select_campaign()



    def on_initialization_error(self, error_msg):

        """Handle initialization error."""

        self.loading_screen.close()

        QMessageBox.critical(self, "Initialization Error", error_msg)

        sys.exit(1)

    def select_campaign(self):
        """Show campaign selection dialog."""
        campaign_dialog = CampaignSelectionDialog(self.memory_system, self)

        if campaign_dialog.exec_() == QDialog.Accepted:
            # Check if new campaign was requested
            if hasattr(campaign_dialog, 'new_campaign_requested') and campaign_dialog.new_campaign_requested:
                # Create new campaign with the provided name
                if hasattr(campaign_dialog, 'new_campaign_name') and campaign_dialog.new_campaign_name:
                    name = campaign_dialog.new_campaign_name
                    # Create the campaign in the main window
                    self.create_new_campaign(name)
                else:
                    self.create_new_campaign()
                return

            # Load selected campaign
            campaign_id = campaign_dialog.selected_campaign_id
            if campaign_id:
                # Try to repair corrupted cards before loading
                self.repair_campaign_cards(campaign_id)

                # Set up UI if needed
                if not hasattr(self, 'game_display') or self.game_display is None:
                    self.setup_ui()
                else:
                    # Clear UI elements
                    self.game_display.clear()
                    self.characters_list.clear()
                    self.locations_list.clear()
                    self.items_list.clear()

                    # Reset info panels
                    self.character_info.update_info(None)
                    self.location_info.update_info(None, None)

                    # Show loading message
                    self.game_display.append(
                        '<div style="color: #9370DB; font-style: italic;">Loading campaign...</div>')
                    QApplication.processEvents()  # Force UI update

                # Load campaign
                success = self.memory_system.load_campaign(campaign_id)
                if success:
                    # Update UI
                    self.update_game_state()
                    self.display_fresh_campaign_message()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to load campaign {campaign_id}")

    def display_fresh_campaign_message(self):
        """Display a fresh welcome message for newly loaded campaign."""
        # Clear display completely
        self.game_display.clear()

        welcome_html = f"""
        <div style="color: #6A5ACD; font-size: 18px; font-weight: bold; margin-bottom: 10px;">
            Campaign: {self.memory_system.campaign_name}
        </div>
        """

        # Get current location
        location_id = self.memory_system.current_focus.get("location")
        location_name = "unknown location"
        location_desc = ""

        if location_id:
            location = self.memory_system.card_manager.get_card(location_id)
            if location:
                location_name = location.name
                location_desc = location.description

        # Add initial game context
        welcome_html += f"""
        <div style="margin-left: 10px;">
            <div style="color: #8A2BE2; font-weight: bold;">Game Master:</div>
            You find yourself in <b>{location_name}</b>. {location_desc}<br>
            What would you like to do?
        </div>
        """

        self.game_display.setHtml(welcome_html)

    def delete_campaign(self, campaign_id):
        """Delete a campaign by ID."""
        import os
        import shutil
        from config import CAMPAIGNS_DIR

        # Verify the campaign exists
        campaign_dir = os.path.join(CAMPAIGNS_DIR, campaign_id)
        if not os.path.exists(campaign_dir):
            return False

        try:
            # Delete all files and subdirectories
            shutil.rmtree(campaign_dir)
            print(f"Deleted campaign: {campaign_id}")
            return True
        except Exception as e:
            print(f"Error deleting campaign: {e}")
            return False

    def fix_campaign_cards(self, campaign_id):

        """Fix corrupted card files in the campaign directory."""

        import os

        import json



        cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "campaigns", campaign_id, "cards")



        if not os.path.exists(cards_dir):

            print(f"Cards directory not found: {cards_dir}")

            return False



        fixed_count = 0



        # Process each card type directory

        for card_type in ["character", "location", "item", "story", "relationship"]:

            type_dir = os.path.join(cards_dir, card_type)



            if not os.path.exists(type_dir):

                os.makedirs(type_dir, exist_ok=True)

                continue



            # Process each card file

            for filename in os.listdir(type_dir):

                if filename.endswith(".json"):

                    file_path = os.path.join(type_dir, filename)



                    try:

                        # Read the file content

                        with open(file_path, "r") as f:

                            content = f.read()



                        # Check if content is a string (corrupted)

                        try:

                            data = json.loads(content)



                            # If data is a string, it's corrupted

                            if isinstance(data, str):

                                # Create a proper card object

                                card_id = filename[:-5]  # Remove .json extension

                                fixed_data = {

                                    "id": card_id,

                                    "type": card_type,

                                    "name": f"Fixed {card_type.capitalize()}",

                                    "description": "This card was recovered from corrupted data",

                                    "creation_time": 0,

                                    "last_modified": 0,

                                    "history": []

                                }



                                # Add type-specific fields

                                if card_type == "character":

                                    fixed_data.update({

                                        "traits": {},

                                        "inventory": [],

                                        "status": "active"

                                    })

                                elif card_type == "location":

                                    fixed_data.update({

                                        "features": [],

                                        "inhabitants": [],

                                        "items": []

                                    })

                                elif card_type == "item":

                                    fixed_data.update({

                                        "properties": {},

                                        "owner": "",

                                        "location": ""

                                    })



                                # Save fixed data

                                with open(file_path, "w") as f:

                                    json.dump(fixed_data, f, indent=2)



                                fixed_count += 1

                                print(f"Fixed corrupted card: {filename}")

                        except (json.JSONDecodeError, TypeError):

                            # Handle completely invalid JSON

                            card_id = filename[:-5]  # Remove .json extension

                            fixed_data = {

                                "id": card_id,

                                "type": card_type,

                                "name": f"Recovered {card_type.capitalize()}",

                                "description": "This card was recovered from invalid data",

                                "creation_time": 0,

                                "last_modified": 0,

                                "history": []

                            }



                            # Add type-specific fields

                            if card_type == "character":

                                fixed_data.update({

                                    "traits": {},

                                    "inventory": [],

                                    "status": "active"

                                })

                            elif card_type == "location":

                                fixed_data.update({

                                    "features": [],

                                    "inhabitants": [],

                                    "items": []

                                })

                            elif card_type == "item":

                                fixed_data.update({

                                    "properties": {},

                                    "owner": "",

                                    "location": ""

                                })



                            # Save fixed data

                            with open(file_path, "w") as f:

                                json.dump(fixed_data, f, indent=2)



                            fixed_count += 1

                            print(f"Fixed invalid card: {filename}")



                    except Exception as e:

                        print(f"Error processing card {filename}: {e}")



        if fixed_count > 0:

            QMessageBox.information(self, "Card Fix", f"Fixed {fixed_count} corrupted card files.")

            print(f"Fixed {fixed_count} card files")



        return fixed_count > 0



    def setup_menu_bar(self):

        """Set up the application menu bar."""

        # Create menu bar

        menu_bar = self.menuBar()



        # File menu

        file_menu = menu_bar.addMenu("&File")



        # New campaign action

        new_campaign_action = QAction("New Campaign", self)

        new_campaign_action.setShortcut("Ctrl+N")

        new_campaign_action.triggered.connect(self.create_new_campaign)

        file_menu.addAction(new_campaign_action)



        # Load campaign action

        load_campaign_action = QAction("Load Campaign", self)

        load_campaign_action.setShortcut("Ctrl+O")

        load_campaign_action.triggered.connect(self.load_campaign)

        file_menu.addAction(load_campaign_action)



        file_menu.addSeparator()



        # Exit action

        exit_action = QAction("Exit", self)

        exit_action.setShortcut("Ctrl+Q")

        exit_action.triggered.connect(self.close)

        file_menu.addAction(exit_action)



        # Create menu

        create_menu = menu_bar.addMenu("&Create")



        # Character action

        create_character_action = QAction("New Character", self)

        create_character_action.triggered.connect(self.create_character)

        create_menu.addAction(create_character_action)



        # Location action

        create_location_action = QAction("New Location", self)

        create_location_action.triggered.connect(self.create_location)

        create_menu.addAction(create_location_action)



        # Item action

        create_item_action = QAction("New Item", self)

        create_item_action.triggered.connect(self.create_item)

        create_menu.addAction(create_item_action)



        # Story action

        create_story_action = QAction("New Story", self)

        create_story_action.triggered.connect(self.create_story)

        create_menu.addAction(create_story_action)



        # Help menu

        help_menu = menu_bar.addMenu("&Help")



        # About action

        about_action = QAction("About", self)

        about_action.triggered.connect(self.show_about)

        help_menu.addAction(about_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        repair_action = QAction("Repair Campaigns", self)
        repair_action.triggered.connect(self.repair_all_campaigns)
        tools_menu.addAction(repair_action)



    def setup_ui(self):

        """Set up the main user interface."""

        # Set up menu bar first

        self.setup_menu_bar()



        # Create the main widget and layout

        main_widget = QWidget()



        # Change to use a vertical QSplitter as the main container instead of QVBoxLayout

        main_splitter = QSplitter(Qt.Vertical)

        main_splitter.setChildrenCollapsible(False)

        main_splitter.setHandleWidth(8)  # Make handles easier to grab

        main_splitter.setOpaqueResize(True)



        # Create header widget to contain campaign name and typing speed

        header_widget = QWidget()

        header_layout = QVBoxLayout(header_widget)

        header_layout.setContentsMargins(10, 5, 10, 5)



        # Create the game header

        header = QLabel(f"Campaign: {self.memory_system.campaign_name}")

        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #6A5ACD; padding: 8px;")

        header_layout.addWidget(header)



        # Create a simplified typing speed control

        speed_layout = QHBoxLayout()

        speed_layout.setContentsMargins(0, 0, 0, 0)



        # Slider label with better styling

        typing_speed_label = QLabel("Typing Speed:")

        typing_speed_label.setStyleSheet("font-weight: bold;")

        speed_layout.addWidget(typing_speed_label)



        # Create an improved slider with REVERSED direction (slow to fast)

        self.typing_speed_slider = QSlider(Qt.Horizontal)

        self.typing_speed_slider.setMinimum(1)  # Now this is SLOW (100ms)

        self.typing_speed_slider.setMaximum(100)  # Now this is FAST (1ms)

        self.typing_speed_slider.setValue(70)  # Default value

        self.typing_speed_slider.setTickPosition(QSlider.TicksBelow)

        self.typing_speed_slider.setTickInterval(10)

        self.typing_speed_slider.setStyleSheet("""

            QSlider::groove:horizontal {

                border: 1px solid #999999;

                height: 8px;

                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 

                                          stop:0 #B592E5, stop:1 #D8BFD8);

                border-radius: 4px;

            }



            QSlider::handle:horizontal {

                background: #9370DB;

                border: 1px solid #5E5E5E;

                width: 18px;

                margin: -5px 0;

                border-radius: 9px;

            }



            QSlider::handle:horizontal:hover {

                background: #8A2BE2;

            }



            QSlider::sub-page:horizontal {

                background: #9370DB;

                border-radius: 4px;

            }



            QSlider::add-page:horizontal {

                background: #E6E6FA;

                border-radius: 4px;

            }



            QSlider::tick-mark:horizontal {

                background: #777777;

                width: 1px;

                height: 3px;

                margin-top: 2px;

            }

        """)

        speed_layout.addWidget(self.typing_speed_slider)

        header_layout.addLayout(speed_layout)



        # Add header to main splitter

        main_splitter.addWidget(header_widget)



        # Create the content splitter (horizontal split between game area and sidebar)

        content_splitter = QSplitter(Qt.Horizontal)

        content_splitter.setChildrenCollapsible(False)

        content_splitter.setHandleWidth(8)

        content_splitter.setOpaqueResize(True)



        # Add the content splitter to the main splitter

        main_splitter.addWidget(content_splitter)



        # Set the main splitter as the central widget

        self.setCentralWidget(main_splitter)



        # Set main splitter sizes (header gets minimal space, content gets the rest)

        main_splitter.setSizes([100, 900])  # Header gets 10%, content gets 90%



        # Create the game vertical splitter

        game_vertical_splitter = QSplitter(Qt.Vertical)

        game_vertical_splitter.setChildrenCollapsible(False)

        game_vertical_splitter.setHandleWidth(8)

        game_vertical_splitter.setOpaqueResize(True)



        # Game display area

        self.game_display = QTextEdit()

        self.game_display.setReadOnly(True)

        self.game_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.game_display.setStyleSheet("""

            background-color: #FFFFFF;

            border: 1px solid #CCCCCC;

            border-radius: 5px;

            padding: 10px;

        """)



        # Set a nicer font

        game_font = QFont("Roboto", 11)

        self.game_display.setFont(game_font)



        game_vertical_splitter.addWidget(self.game_display)



        # User input area

        input_widget = QWidget()

        input_layout = QHBoxLayout(input_widget)

        input_layout.setContentsMargins(0, 5, 0, 0)



        self.user_input = QLineEdit()

        self.user_input.setPlaceholderText("Enter your action or dialogue...")

        self.user_input.setStyleSheet("""

            background-color: #FFFFFF;

            border: 1px solid #CCCCCC;

            border-radius: 5px;

            padding: 8px;

        """)

        self.user_input.returnPressed.connect(self.process_input)



        self.send_button = QPushButton("Send")

        self.send_button.setStyleSheet("""

            QPushButton {

                background-color: #9370DB;

                color: white;

                border: none;

                border-radius: 5px;

                padding: 8px 12px;

            }

            QPushButton:hover {

                background-color: #8A2BE2;

            }

        """)

        self.send_button.clicked.connect(self.process_input)



        input_layout.addWidget(self.user_input)

        input_layout.addWidget(self.send_button)



        game_vertical_splitter.addWidget(input_widget)

        game_vertical_splitter.setSizes([800, 100])  # Text area gets 80%, input gets 20%



        # Add the game splitter to the content splitter

        content_splitter.addWidget(game_vertical_splitter)



        # Sidebar for game state

        sidebar = QTabWidget()

        sidebar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        sidebar.setStyleSheet("""

            QTabWidget::pane {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

            }

            QTabBar::tab {

                background-color: #E6E6FA;

                border: 1px solid #CCCCCC;

                border-bottom-color: #CCCCCC;

                border-top-left-radius: 4px;

                border-top-right-radius: 4px;

                padding: 6px 10px;

            }

            QTabBar::tab:selected, QTabBar::tab:hover {

                background-color: #D8BFD8;

            }

            QTabBar::tab:selected {

                border-bottom-color: #D8BFD8;

            }

        """)



        # Characters tab

        characters_tab = QWidget()

        characters_layout = QVBoxLayout(characters_tab)



        # Characters list

        self.characters_list = QListWidget()

        self.characters_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.characters_list.setMinimumHeight(100)

        self.characters_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Character info panel

        self.character_info = CharacterInfoWidget()

        self.character_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.character_info.setMinimumHeight(200)



        # Split the tab into list and details

        char_splitter = QSplitter(Qt.Vertical)

        char_splitter.setChildrenCollapsible(False)  # Prevent sections from collapsing completely

        char_splitter.setHandleWidth(8)  # Make handles easier to grab

        char_splitter.setOpaqueResize(True)  # Resize in real-time for better UX

        char_splitter.addWidget(self.characters_list)

        char_splitter.addWidget(self.character_info)



        # Set stretch factors for better resizing behavior

        char_splitter.setStretchFactor(0, 1)  # Character list gets 1 part

        char_splitter.setStretchFactor(1, 2)  # Character details get 2 parts



        characters_layout.addWidget(char_splitter)

        sidebar.addTab(characters_tab, "Characters")



        # Locations tab

        locations_tab = QWidget()

        locations_layout = QVBoxLayout(locations_tab)



        # Locations list

        self.locations_list = QListWidget()

        self.locations_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.locations_list.setMinimumHeight(100)

        self.locations_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        # Location info panel

        self.location_info = LocationInfoWidget()

        self.location_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.location_info.setMinimumHeight(200)



        # Split the tab into list and details

        loc_splitter = QSplitter(Qt.Vertical)

        loc_splitter.setChildrenCollapsible(False)  # Prevent sections from collapsing completely

        loc_splitter.setHandleWidth(8)  # Make handles easier to grab

        loc_splitter.setOpaqueResize(True)  # Resize in real-time for better UX

        loc_splitter.addWidget(self.locations_list)

        loc_splitter.addWidget(self.location_info)



        # Set stretch factors for better resizing behavior

        loc_splitter.setStretchFactor(0, 1)  # Location list gets 1 part

        loc_splitter.setStretchFactor(1, 2)  # Location details get 2 parts



        locations_layout.addWidget(loc_splitter)

        sidebar.addTab(locations_tab, "Locations")



        # Items tab

        items_tab = QWidget()

        items_layout = QVBoxLayout(items_tab)



        # Items list

        self.items_list = QListWidget()

        self.items_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.items_list.setMinimumHeight(150)

        self.items_list.setStyleSheet("""

            QListWidget {

                border: 1px solid #CCCCCC;

                border-radius: 5px;

                background-color: white;

            }

            QListWidget::item {

                padding: 6px;

                border-bottom: 1px solid #EEEEEE;

            }

            QListWidget::item:selected {

                background-color: #E6E6FA;

                color: black;

            }

            QListWidget::item:hover {

                background-color: #F5F5F5;

            }

        """)



        items_layout.addWidget(self.items_list)

        sidebar.addTab(items_tab, "Items")



        # Connect signals

        self.characters_list.currentItemChanged.connect(self.on_character_selected)

        self.locations_list.currentItemChanged.connect(self.on_location_selected)



        # Add sidebar to content splitter

        content_splitter.addWidget(sidebar)



        # Set initial content splitter sizes

        content_splitter.setSizes([700, 300])  # Game area gets 70%, sidebar gets 30%



        # Connect the slider to update the typing speed

        self.typing_speed_slider.valueChanged.connect(self.update_typing_speed_with_indicator)



        # Initialize game state

        self.update_game_state()



        # Display welcome message

        self.display_welcome_message()



    def update_typing_speed_with_indicator(self, value):

        """Update the typing speed and indicator when the slider is moved."""

        # REVERSED: Convert slider value to typing speed (slider: 1=slow to 100=fast)

        # We need to invert this so that 1 on slider = 100ms delay, 100 on slider = 1ms delay

        self.typing_speed = 101 - value  # Reversing the slider value



        # If typing is in progress, update the timer interval

        if self.typing_in_progress and self.typing_timer is not None and self.typing_timer.isActive():

            self.typing_timer.setInterval(self.typing_speed)



    def set_lavender_theme(self):

        """Set the lavender color scheme for the application."""

        qss = """

        QMainWindow {

            background-color: #F5F0FF;

        }

        QWidget {

            background-color: #F5F0FF;

            color: #333333;

        }

        QTabWidget {

            background-color: #F5F0FF;

        }

        QTabWidget::pane {

            border: 1px solid #CCCCCC;

            border-radius: 5px;

        }

        QTabBar::tab {

            background-color: #E6E6FA;

            border: 1px solid #CCCCCC;

            border-bottom-color: #CCCCCC;

            border-top-left-radius: 4px;

            border-top-right-radius: 4px;

            padding: 6px 10px;

        }

        QTabBar::tab:selected, QTabBar::tab:hover {

            background-color: #D8BFD8;

        }

        QTabBar::tab:selected {

            border-bottom-color: #D8BFD8;

        }

        QScrollBar:vertical {

            border: none;

            background: #F0F0F0;

            width: 12px;

            margin: 0px;

        }

        QScrollBar::handle:vertical {

            background: #B0A0C7;

            min-height: 20px;

            border-radius: 6px;

        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {

            border: none;

            background: none;

            height: 0px;

        }

        QScrollBar:horizontal {

            border: none;

            background: #F0F0F0;

            height: 12px;

            margin: 0px;

        }

        QScrollBar::handle:horizontal {

            background: #B0A0C7;

            min-width: 20px;

            border-radius: 6px;

        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {

            border: none;

            background: none;

            width: 0px;

        }

        """

        self.setStyleSheet(qss)

    def display_welcome_message(self):
        """Display the welcome message in the game display."""
        # Clear any previous content
        self.game_display.clear()

        welcome_html = """
        <div style="color: #6A5ACD; font-size: 18px; font-weight: bold; margin-bottom: 10px;">
            Welcome to Campaign
        </div>
        <div style="margin-bottom: 15px;">
            You are playing in <b>{campaign_name}</b>
        </div>
        <div style="color: #8A2BE2; font-weight: bold; margin-top: 10px; margin-bottom: 5px;">
            Game Master:
        </div>
        """.format(campaign_name=self.memory_system.campaign_name)

        # Get current location
        location_id = self.memory_system.current_focus.get("location")
        location_name = "unknown location"
        location_desc = ""

        if location_id:
            location = self.memory_system.card_manager.get_card(location_id)
            if location:
                location_name = location.name
                location_desc = location.description

        # Add initial game context
        welcome_html += f"""
        <div style="margin-left: 10px;">
            You find yourself in <b>{location_name}</b>. {location_desc}<br>
            What would you like to do?
        </div>
        """

        self.game_display.setHtml(welcome_html)


    def update_game_state(self):

        """Update game state UI elements."""

        # Update character list

        self.characters_list.clear()

        for char_id, character in self.memory_system.card_manager.cards_by_type.get("character", {}).items():

            status = getattr(character, "status", "")

            status_text = f" ({status})" if status else ""

            item = QListWidgetItem(f"{character.name}{status_text}")

            item.setData(Qt.UserRole, char_id)

            self.characters_list.addItem(item)



        # Update location list

        self.locations_list.clear()

        for loc_id, location in self.memory_system.card_manager.cards_by_type.get("location", {}).items():

            item = QListWidgetItem(location.name)

            item.setData(Qt.UserRole, loc_id)

            self.locations_list.addItem(item)



            # Highlight current location

            if loc_id == self.memory_system.current_focus.get("location"):

                item.setBackground(QColor("#E6E6FA"))

                item.setText(f"➤ {location.name}")

                self.locations_list.setCurrentItem(item)



        # Update items list

        self.items_list.clear()

        for item_id, item in self.memory_system.card_manager.cards_by_type.get("item", {}).items():

            location_id = getattr(item, "location", "")

            owner_id = getattr(item, "owner", "")



            location_text = ""

            if location_id:

                location = self.memory_system.card_manager.get_card(location_id)

                if location:

                    location_text = f" (at {location.name})"



            owner_text = ""

            if owner_id:

                owner = self.memory_system.card_manager.get_card(owner_id)

                if owner:

                    owner_text = f" (owned by {owner.name})"



            list_item = QListWidgetItem(f"{item.name}{location_text}{owner_text}")

            list_item.setData(Qt.UserRole, item_id)

            self.items_list.addItem(list_item)



    def on_character_selected(self, current, previous):

        """Handle character selection in the list."""

        if not current:

            self.character_info.update_info(None)

            return



        character_id = current.data(Qt.UserRole)

        character = self.memory_system.card_manager.get_card(character_id)

        self.character_info.update_info(character)



        # Add context menu to character info widget

        self.character_info.setContextMenuPolicy(Qt.CustomContextMenu)

        self.character_info.customContextMenuRequested.connect(

            lambda pos: self.show_character_context_menu(pos, character_id))



    def show_characters_context_menu(self, position):

        """Show context menu for characters list."""

        menu = QMenu()



        # Get selected item

        selected_item = self.characters_list.itemAt(position)

        if selected_item:

            character_id = selected_item.data(Qt.UserRole)



            edit_action = menu.addAction("Edit Character")

            edit_action.triggered.connect(lambda: self.edit_character(character_id))



            teleport_action = menu.addAction("Teleport to Current Location")

            teleport_action.triggered.connect(lambda: self.teleport_character(character_id))



            delete_action = menu.addAction("Delete Character")

            delete_action.triggered.connect(lambda: self.delete_character(character_id))



        # Always add "Add New" option

        menu.addSeparator()

        add_action = menu.addAction("Add New Character")

        add_action.triggered.connect(self.create_character)



        menu.exec_(self.characters_list.mapToGlobal(position))



    def teleport_character(self, character_id):

        """Teleport a character to the current location."""

        character = self.memory_system.card_manager.get_card(character_id)

        if not character:

            return



        location_id = self.memory_system.current_focus.get("location")

        if not location_id:

            QMessageBox.warning(self, "No Location", "No current location set.")

            return



        location = self.memory_system.card_manager.get_card(location_id)

        if not location:

            QMessageBox.warning(self, "Invalid Location", "Current location is invalid.")

            return



        # Update character location

        self.memory_system.card_manager.update_card(

            character_id,

            {"location": location_id},

            "user_edit"

        )



        # Update UI

        self.update_game_state()



        # Show message

        QMessageBox.information(self, "Character Teleported",

                                f"{character.name} has been teleported to {location.name}.")



        # Add to current characters in focus

        if character_id not in self.memory_system.current_focus.get("characters", []):

            self.memory_system.current_focus["characters"].append(character_id)

            self.memory_system._save_campaign_metadata()



    def save_campaign(self):

        """Explicitly save the current campaign state."""

        if not self.memory_system or not hasattr(self.memory_system, '_save_campaign_metadata'):

            QMessageBox.warning(self, "Error", "No campaign loaded.")

            return



        try:

            # Force save by setting last save time to 0

            self.memory_system._last_metadata_save = 0

            self.memory_system._save_campaign_metadata()



            QMessageBox.information(self, "Campaign Saved", "Campaign has been saved successfully.")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Failed to save campaign: {str(e)}")



    def on_location_selected(self, current, previous):

        """Handle location selection in the list."""

        if not current:

            self.location_info.update_info(None, None)

            return



        location_id = current.data(Qt.UserRole)

        location = self.memory_system.card_manager.get_card(location_id)

        self.location_info.update_info(location, self.memory_system)



        # Add context menu to location info widget

        self.location_info.setContextMenuPolicy(Qt.CustomContextMenu)

        self.location_info.customContextMenuRequested.connect(

            lambda pos: self.show_location_context_menu(pos, location_id))



    def show_locations_context_menu(self, position):

        """Show context menu for locations list."""

        menu = QMenu()



        # Get selected item

        selected_item = self.locations_list.itemAt(position)

        if selected_item:

            location_id = selected_item.data(Qt.UserRole)



            edit_action = menu.addAction("Edit Location")

            edit_action.triggered.connect(lambda: self.edit_location(location_id))



            set_current_action = menu.addAction("Set as Current Location")

            set_current_action.triggered.connect(lambda: self.set_current_location(location_id))



            delete_action = menu.addAction("Delete Location")

            delete_action.triggered.connect(lambda: self.delete_location(location_id))



        # Always add "Add New" option

        menu.addSeparator()

        add_action = menu.addAction("Add New Location")

        add_action.triggered.connect(self.create_location)



        menu.exec_(self.locations_list.mapToGlobal(position))



    def show_items_context_menu(self, position):

        """Show context menu for items list."""

        menu = QMenu()



        # Get selected item

        selected_item = self.items_list.itemAt(position)

        if selected_item:

            item_id = selected_item.data(Qt.UserRole)



            edit_action = menu.addAction("Edit Item")

            edit_action.triggered.connect(lambda: self.edit_item(item_id))



            delete_action = menu.addAction("Delete Item")

            delete_action.triggered.connect(lambda: self.delete_item(item_id))



        # Always add "Add New" option

        menu.addSeparator()

        add_action = menu.addAction("Add New Item")

        add_action.triggered.connect(self.create_item)



        menu.exec_(self.items_list.mapToGlobal(position))



    def set_current_location(self, location_id):

        """Set a location as the current focus location."""

        location = self.memory_system.card_manager.get_card(location_id)

        if not location:

            return



        # Update current focus

        self.memory_system.current_focus["location"] = location_id

        self.memory_system._save_campaign_metadata()



        # Update UI

        self.update_game_state()



        # Show message

        QMessageBox.information(self, "Location Set",

                                f"{location.name} has been set as the current location.")



    def process_input(self):

        """Process user input and get AI response."""

        user_text = self.user_input.text().strip()

        if not user_text:

            return



        # Clear input field

        self.user_input.clear()



        # Disable input controls while processing

        self.user_input.setEnabled(False)

        self.send_button.setEnabled(False)



        # Display user input

        self.game_display.append(f'<div style="color: #333333; margin-top: 10px;"><b>You:</b> {user_text}</div>')



        # Process in separate thread to avoid freezing UI

        class ResponseThread(QThread):

            response_ready = pyqtSignal(str)



            def __init__(self, memory_system, user_input):

                super().__init__()

                self.memory_system = memory_system

                self.user_input = user_input



            def run(self):

                try:

                    # Let system process the turn

                    response = self.memory_system.process_turn(self.user_input)

                    self.response_ready.emit(response)

                except Exception as e:

                    self.response_ready.emit(f"Error: {str(e)}")



        # Create and start thread

        self.response_thread = ResponseThread(self.memory_system, user_text)

        self.response_thread.response_ready.connect(self.display_response)

        self.response_thread.start()



        # Show "thinking" indicator

        self.game_display.append(

            '<div style="color: #9370DB; font-style: italic; margin-top: 5px;">Game Master is thinking...</div>')



        # Scroll to bottom

        self.game_display.moveCursor(QTextCursor.End)



    def display_response(self, response):

        """Display the AI response in the game display with typewriter effect."""

        # Remove thinking indicator (last line)

        cursor = self.game_display.textCursor()

        cursor.movePosition(QTextCursor.End)

        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)

        cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)

        cursor.removeSelectedText()



        # Add the start of response

        self.game_display.append(f'<div style="color: #8A2BE2; margin-top: 5px;"><b>Game Master:</b> </div>')



        # Set up typewriter effect

        self.current_response = response

        self.current_position = 0

        self.typing_in_progress = True



        # Create and start the timer for typewriter effect

        self.typing_timer = QTimer(self)

        self.typing_timer.timeout.connect(self.type_next_character)

        self.typing_timer.start(self.typing_speed)  # Use the user-defined typing speed



        # Scroll to bottom

        self.game_display.moveCursor(QTextCursor.End)



    def type_next_character(self):

        """Add the next character to the response for typewriter effect."""

        if self.current_position < len(self.current_response):

            # Get current text cursor position

            cursor = self.game_display.textCursor()

            cursor.movePosition(QTextCursor.End)



            # Get the character to add

            char = self.current_response[self.current_position]

            cursor.insertText(char)



            # Update position for next character

            self.current_position += 1



            # Scroll to ensure typed text is visible

            self.game_display.setTextCursor(cursor)

        else:

            # Typing complete

            self.typing_timer.stop()

            self.typing_in_progress = False



            # Add a newline once complete

            cursor = self.game_display.textCursor()

            cursor.movePosition(QTextCursor.End)

            cursor.insertText("\n")



            # Re-enable input when typing is done

            self.user_input.setEnabled(True)

            self.send_button.setEnabled(True)

            self.user_input.setFocus()



            # Update game state

            self.update_game_state()

    def load_campaign(self):
        """Load an existing campaign."""
        campaign_dialog = CampaignSelectionDialog(self.memory_system, self)
        if campaign_dialog.exec_() == QDialog.Accepted:
            # Load selected campaign
            campaign_id = campaign_dialog.selected_campaign_id
            if campaign_id:
                # Repair the selected campaign specifically
                fixed_count = self.repair_campaign_cards(campaign_id)
                if fixed_count > 0:
                    QMessageBox.information(self, "Campaign Repair",
                                            f"Fixed {fixed_count} issues in selected campaign.")

                # Clear the current game display
                self.game_display.clear()

                # Show loading indicator

                self.game_display.append(

                    '<div style="color: #9370DB; font-style: italic;">Loading campaign history...</div>')

                QApplication.processEvents()  # Update the UI

                # Load campaign

                success = self.memory_system.load_campaign(campaign_id)



                if success:

                    # Update the UI

                    self.update_game_state()



                    # Display welcome back message

                    welcome_html = f"""

                    <div style="color: #6A5ACD; font-size: 18px; font-weight: bold; margin-bottom: 10px;">

                        Welcome back to "{self.memory_system.campaign_name}"

                    </div>

                    """



                    # Display previous conversation history

                    self.game_display.clear()

                    self.game_display.setHtml(welcome_html)



                    # Display previous session history

                    if self.memory_system.session_history:

                        self.game_display.append(

                            '<div style="color: #8A2BE2; font-weight: bold;">Previous Conversation:</div>')



                        # Display last 10 interactions or all if less than 10

                        history_to_show = self.memory_system.session_history[-10:] if len(

                            self.memory_system.session_history) > 10 else self.memory_system.session_history



                        if len(self.memory_system.session_history) > 10:

                            self.game_display.append(

                                '<div style="color: #888888; font-style: italic;">(Showing last 10 interactions)</div>')



                        for interaction in history_to_show:

                            user_text = interaction.get('user', '')

                            ai_text = interaction.get('ai', '')



                            if user_text:

                                self.game_display.append(

                                    f'<div style="color: #333333; margin-top: 10px;"><b>You:</b> {user_text}</div>')



                            if ai_text:

                                self.game_display.append(

                                    f'<div style="color: #8A2BE2; margin-top: 5px;"><b>Game Master:</b> {ai_text}</div>')



                        # Add separator

                        self.game_display.append(

                            '<div style="border-bottom: 1px solid #CCCCCC; margin: 15px 0;"></div>')



                    # Get current location for context

                    location_id = self.memory_system.current_focus.get("location")

                    location_name = "unknown location"



                    if location_id:

                        location = self.memory_system.card_manager.get_card(location_id)

                        if location:

                            location_name = location.name



                    # Add current status

                    self.game_display.append(

                        f'<div style="color: #8A2BE2;"><b>Game Master:</b> You are currently in {location_name}. What would you like to do?</div>')



                    # Scroll to bottom

                    self.game_display.moveCursor(QTextCursor.End)

                else:

                    QMessageBox.critical(self, "Error", f"Failed to load campaign {campaign_id}")



    def create_character(self):

        """Create a new character."""

        dialog = CharacterDialog(self.memory_system, parent=self)

        if dialog.exec_() == QDialog.Accepted:

            # Get character data

            character_data = dialog.get_character_data()



            # Create character

            self.memory_system.card_manager.create_card(

                "character",

                character_data["name"],

                character_data

            )



            # Update the UI

            self.update_game_state()



            # Show success message

            QMessageBox.information(self, "Character Created",

                                    f"Character '{character_data['name']}' created successfully!")



    def edit_character(self, character_id):

        """Edit an existing character."""

        character = self.memory_system.card_manager.get_card(character_id)

        if character:

            dialog = CharacterDialog(self.memory_system, character, parent=self)

            if dialog.exec_() == QDialog.Accepted:

                # Get updated character data

                character_data = dialog.get_character_data()



                # Update character

                self.memory_system.card_manager.update_card(

                    character_id,

                    character_data,

                    "user_edit"

                )



                # Update the UI

                self.update_game_state()



                # Show success message

                QMessageBox.information(self, "Character Updated",

                                        f"Character '{character_data['name']}' updated successfully!")



    def delete_character(self, character_id):

        """Delete an existing character."""

        character = self.memory_system.card_manager.get_card(character_id)

        if character:

            confirm = QMessageBox.question(

                self, "Confirm Deletion",

                f"Are you sure you want to delete character '{character.name}'?",

                QMessageBox.Yes | QMessageBox.No

            )



            if confirm == QMessageBox.Yes:

                # Delete character

                success = self.memory_system.card_manager.delete_card(character_id)



                if success:

                    # Update the UI

                    self.update_game_state()



                    # Show success message

                    QMessageBox.information(self, "Character Deleted",

                                            f"Character '{character.name}' deleted successfully!")

                else:

                    QMessageBox.critical(self, "Error", f"Failed to delete character '{character.name}'")



    def create_location(self):

        """Create a new location."""

        dialog = LocationDialog(self.memory_system, parent=self)

        if dialog.exec_() == QDialog.Accepted:

            # Get location data

            location_data = dialog.get_location_data()



            # Create location

            self.memory_system.card_manager.create_card(

                "location",

                location_data["name"],

                location_data

            )



            # Update the UI

            self.update_game_state()



            # Show success message

            QMessageBox.information(self, "Location Created",

                                    f"Location '{location_data['name']}' created successfully!")



    def edit_location(self, location_id):

        """Edit an existing location."""

        location = self.memory_system.card_manager.get_card(location_id)

        if location:

            dialog = LocationDialog(self.memory_system, location, parent=self)

            if dialog.exec_() == QDialog.Accepted:

                # Get updated location data

                location_data = dialog.get_location_data()



                # Update location

                self.memory_system.card_manager.update_card(

                    location_id,

                    location_data,

                    "user_edit"

                )



                # Update the UI

                self.update_game_state()



                # Show success message

                QMessageBox.information(self, "Location Updated",

                                        f"Location '{location_data['name']}' updated successfully!")



    def delete_location(self, location_id):

        """Delete an existing location."""

        location = self.memory_system.card_manager.get_card(location_id)

        if location:

            confirm = QMessageBox.question(

                self, "Confirm Deletion",

                f"Are you sure you want to delete location '{location.name}'?",

                QMessageBox.Yes | QMessageBox.No

            )



            if confirm == QMessageBox.Yes:

                # Delete location

                success = self.memory_system.card_manager.delete_card(location_id)



                if success:

                    # Update the UI

                    self.update_game_state()



                    # Show success message

                    QMessageBox.information(self, "Location Deleted",

                                            f"Location '{location.name}' deleted successfully!")

                else:

                    QMessageBox.critical(self, "Error", f"Failed to delete location '{location.name}'")



    def create_item(self):

        """Create a new item."""

        dialog = ItemDialog(self.memory_system, parent=self)

        if dialog.exec_() == QDialog.Accepted:

            # Get item data

            item_data = dialog.get_item_data()



            # Create item

            self.memory_system.card_manager.create_card(

                "item",

                item_data["name"],

                item_data

            )



            # Update the UI

            self.update_game_state()



            # Show success message

            QMessageBox.information(self, "Item Created",

                                    f"Item '{item_data['name']}' created successfully!")



    def create_story(self):

        """Create a new story element."""

        dialog = StoryDialog(self.memory_system, parent=self)

        if dialog.exec_() == QDialog.Accepted:

            # Get story data

            story_data = dialog.get_story_data()



            # Create story

            self.memory_system.card_manager.create_card(

                "story",

                story_data["name"],

                story_data

            )



            # Update the UI

            self.update_game_state()



            # Show success message

            QMessageBox.information(self, "Story Created",

                                    f"Story '{story_data['name']}' created successfully!")



    def show_about(self):

        """Show about dialog."""

        QMessageBox.about(self, "About AI Narrative RPG",

                          "AI Narrative RPG System\n\n"

                          "A text-based RPG system with AI-powered storytelling.\n\n"

                          "Features:\n"

                          "- Dynamic narrative generation\n"

                          "- Memory system for story consistency\n"

                          "- Multiple LLM provider support\n"

                          "- Card-based entity management")

    def repair_campaign_cards(self, campaign_id, silent=False):
        """Repair corrupted card files in a campaign."""
        import os
        import json
        import time
        from config import CAMPAIGNS_DIR

        cards_dir = os.path.join(CAMPAIGNS_DIR, campaign_id, "cards")

        if not os.path.exists(cards_dir):
            if not silent:
                print(f"Cards directory not found: {cards_dir}")
            return 0

        fixed_count = 0

        # Process each card type directory
        for card_type in ["character", "location", "item", "story", "relationship"]:
            type_dir = os.path.join(cards_dir, card_type)

            if not os.path.exists(type_dir):
                os.makedirs(type_dir, exist_ok=True)
                continue

            # Process each card file
            for filename in os.listdir(type_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(type_dir, filename)

                    try:
                        # Read the file content
                        with open(file_path, "r") as f:
                            content = f.read()

                        # Check if content is a string (corrupted)
                        try:
                            data = json.loads(content)

                            # If data is a string or not a dictionary, it's corrupted
                            if isinstance(data, str) or not isinstance(data, dict):
                                # Create a proper card object
                                card_id = filename[:-5]  # Remove .json extension
                                fixed_data = {
                                    "id": card_id,
                                    "type": card_type,
                                    "name": f"Fixed {card_type.capitalize()}",
                                    "description": "This card was recovered from corrupted data",
                                    "creation_time": time.time(),
                                    "last_modified": time.time(),
                                    "history": []
                                }

                                # Add type-specific fields
                                if card_type == "character":
                                    fixed_data.update({
                                        "traits": {},
                                        "inventory": [],
                                        "status": "active"
                                    })
                                elif card_type == "location":
                                    fixed_data.update({
                                        "features": [],
                                        "inhabitants": [],
                                        "items": []
                                    })
                                elif card_type == "item":
                                    fixed_data.update({
                                        "properties": {},
                                        "owner": "",
                                        "location": ""
                                    })

                                # Save fixed data
                                with open(file_path, "w") as f:
                                    json.dump(fixed_data, f, indent=2)

                                fixed_count += 1
                                if not silent:
                                    print(f"Fixed corrupted card: {filename}")
                        except (json.JSONDecodeError, TypeError):
                            # Handle completely invalid JSON
                            card_id = filename[:-5]  # Remove .json extension
                            fixed_data = {
                                "id": card_id,
                                "type": card_type,
                                "name": f"Recovered {card_type.capitalize()}",
                                "description": "This card was recovered from invalid data",
                                "creation_time": time.time(),
                                "last_modified": time.time(),
                                "history": []
                            }

                            # Add type-specific fields
                            if card_type == "character":
                                fixed_data.update({
                                    "traits": {},
                                    "inventory": [],
                                    "status": "active"
                                })
                            elif card_type == "location":
                                fixed_data.update({
                                    "features": [],
                                    "inhabitants": [],
                                    "items": []
                                })
                            elif card_type == "item":
                                fixed_data.update({
                                    "properties": {},
                                    "owner": "",
                                    "location": ""
                                })

                            # Save fixed data
                            with open(file_path, "w") as f:
                                json.dump(fixed_data, f, indent=2)

                            fixed_count += 1
                            if not silent:
                                print(f"Fixed invalid card: {filename}")

                    except Exception as e:
                        if not silent:
                            print(f"Error processing card {filename}: {e}")

        if fixed_count > 0 and not silent:
            QMessageBox.information(self, "Card Fix", f"Fixed {fixed_count} corrupted card files.")

        return fixed_count

    def create_new_campaign(self, name=None):
        """Create a new campaign from the main GUI."""
        # Get campaign name if not provided
        if name is None:
            name, ok = QInputDialog.getText(self, "New Campaign", "Enter campaign name:")
            if not ok or not name:
                return

        # Create basic setup
        initial_setup = {
            "locations": [
                {
                    "name": "Town Square",
                    "description": "The central gathering place in the village. A fountain bubbles in the center.",
                    "features": ["fountain", "benches", "cobblestone ground"]
                }
            ],
            "characters": [
                {
                    "name": "Old Wizard",
                    "description": "An elderly wizard with a long white beard and blue robes.",
                    "traits": {"wisdom": "high", "strength": "low", "magic": "powerful"},
                    "location": "0"  # Will be replaced with Town Square ID
                }
            ],
            "items": [
                {
                    "name": "Magic Scroll",
                    "description": "An ancient scroll with glowing runes.",
                    "location": "0"  # Will be replaced with Town Square ID
                }
            ],
            "initial_focus": {
                "characters": ["0"],
                "location": "0",
                "items": ["0"]
            }
        }

        # Create the campaign
        success = self.memory_system.create_new_campaign(name, initial_setup)

        if success:
            # Check if UI is initialized before updating
            if hasattr(self, 'characters_list') and self.characters_list is not None:
                # Update UI with new campaign
                self.update_game_state()
                self.display_fresh_campaign_message()
            else:
                # Set up UI first
                self.setup_ui()
                # Then update with campaign data
                self.update_game_state()
                self.display_fresh_campaign_message()

            # Show success message
            QMessageBox.information(self, "Campaign Created", f"Campaign '{name}' created successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Failed to create campaign '{name}'")


    def repair_all_campaigns(self):
        """Repair all campaigns with corrupted card files."""
        # Get all campaigns
        if not hasattr(self, 'memory_system') or self.memory_system is None:
            return

        campaigns = self.memory_system.get_available_campaigns()
        if not campaigns:
            return

        total_fixed = 0
        fixed_campaigns = []

        # Show progress dialog
        progress = QProgressDialog("Checking campaigns for corruption...", None, 0, len(campaigns), self)
        progress.setWindowTitle("Campaign Repair")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        for i, campaign in enumerate(campaigns):
            campaign_id = campaign.get("id")
            if campaign_id:
                # Update progress dialog
                progress.setValue(i)
                progress.setLabelText(f"Checking campaign: {campaign.get('name', 'Unknown')}")
                QApplication.processEvents()

                # Attempt repair
                fixed_count = self.repair_campaign_cards(campaign_id, silent=True)
                if fixed_count > 0:
                    total_fixed += fixed_count
                    fixed_campaigns.append(campaign.get("name", campaign_id))

        progress.setValue(len(campaigns))

        # Show results if any repairs were made
        if total_fixed > 0:
            campaign_names = ", ".join(fixed_campaigns)
            QMessageBox.information(
                self,
                "Campaign Repair",
                f"Repaired {total_fixed} card files across {len(fixed_campaigns)} campaigns:\n{campaign_names}"
            )





# Main app entry point

if __name__ == "__main__":

    app = QApplication(sys.argv)



    # Set application font

    app_font = QFont("Roboto", 10)

    app.setFont(app_font)



    window = RpgNarrativeGUI()

    window.show()



    sys.exit(app.exec_())