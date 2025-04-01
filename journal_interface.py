import time
from PyQt6.QtWidgets import (QTabWidget, QVBoxLayout, QHBoxLayout, QWidget, QListWidget,
                             QLabel, QPushButton, QTextEdit, QScrollArea, QSplitter,
                             QFrame, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon, QPalette


class GameJournal(QTabWidget):
    """An enhanced journal interface for the game"""

    def __init__(self, parent=None, game_state=None, accent_color="#7E57C2", highlight_color="#4A2D7D"):
        super().__init__(parent)
        self.game_state = game_state
        self.ACCENT_COLOR = accent_color
        self.HIGHLIGHT_COLOR = highlight_color
        self.last_update_time = time.time()
        self.updated_items = []

        # Set up UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the journal UI with tabs"""
        # Style the tab widget
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}

            QTabBar::tab {{
                background-color: #E1D4F2;
                color: #3A1E64;
                border: 1px solid {self.ACCENT_COLOR};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
                margin-right: 2px;
                min-width: 80px;
            }}

            QTabBar::tab:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
                border: 1px solid {self.HIGHLIGHT_COLOR};
                border-bottom: none;
            }}
        """)

        # Create tabs
        self.quests_tab = self.create_quests_tab()
        self.npcs_tab = self.create_npcs_tab()
        self.locations_tab = self.create_locations_tab()
        self.memories_tab = self.create_memories_tab()
        self.inventory_tab = self.create_inventory_tab()

        # Add tabs to the widget
        self.addTab(self.quests_tab, "Quests")
        self.addTab(self.npcs_tab, "Characters")
        self.addTab(self.locations_tab, "Locations")
        self.addTab(self.inventory_tab, "Inventory")
        self.addTab(self.memories_tab, "Memories")

        # Create a timer to clear highlighting after some time
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self.clear_highlights)

    def create_quests_tab(self):
        """Create the quests tab with list and details view"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Create the quests list panel
        quests_panel = QWidget()
        quests_layout = QVBoxLayout(quests_panel)

        # Add header
        header_label = QLabel("Active Quests")
        header_label.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        quests_layout.addWidget(header_label)

        # Create quest lists (active and completed)
        self.active_quests_list = QListWidget()
        self.active_quests_list.setMaximumHeight(150)
        self.active_quests_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        self.active_quests_list.itemClicked.connect(self.show_quest_details)
        quests_layout.addWidget(self.active_quests_list)

        # Add completed quests header
        completed_header = QLabel("Completed Quests")
        completed_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        quests_layout.addWidget(completed_header)

        # Completed quests list
        self.completed_quests_list = QListWidget()
        self.completed_quests_list.setMaximumHeight(100)
        self.completed_quests_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid #E1D4F2;
                color: #3A1E64;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        self.completed_quests_list.itemClicked.connect(self.show_quest_details)
        quests_layout.addWidget(self.completed_quests_list)

        # Create the quest details panel
        details_panel = QScrollArea()
        details_panel.setWidgetResizable(True)
        details_panel.setFrameShape(QFrame.Shape.NoFrame)

        self.quest_details_widget = QWidget()
        self.quest_details_layout = QVBoxLayout(self.quest_details_widget)

        # Add a placeholder label
        placeholder = QLabel("Select a quest to view details")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.quest_details_layout.addWidget(placeholder)

        details_panel.setWidget(self.quest_details_widget)

        # Add panels to the splitter
        splitter.addWidget(quests_panel)
        splitter.addWidget(details_panel)

        # Set initial sizes
        splitter.setSizes([200, 300])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def create_npcs_tab(self):
        """Create the NPCs/characters tab with list and details view"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Create the NPCs list panel
        npcs_panel = QWidget()
        npcs_layout = QVBoxLayout(npcs_panel)

        # Add header
        header_label = QLabel("Characters")
        header_label.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        npcs_layout.addWidget(header_label)

        # Create NPC list
        self.npcs_list = QListWidget()
        self.npcs_list.setMaximumHeight(200)
        self.npcs_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        self.npcs_list.itemClicked.connect(self.show_npc_details)
        npcs_layout.addWidget(self.npcs_list)

        # Create the NPC details panel
        details_panel = QScrollArea()
        details_panel.setWidgetResizable(True)
        details_panel.setFrameShape(QFrame.Shape.NoFrame)

        self.npc_details_widget = QWidget()
        self.npc_details_layout = QVBoxLayout(self.npc_details_widget)

        # Add a placeholder label
        placeholder = QLabel("Select a character to view details")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.npc_details_layout.addWidget(placeholder)

        details_panel.setWidget(self.npc_details_widget)

        # Add panels to the splitter
        splitter.addWidget(npcs_panel)
        splitter.addWidget(details_panel)

        # Set initial sizes
        splitter.setSizes([150, 350])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def create_locations_tab(self):
        """Create the locations tab with list and details view"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Create the locations list panel
        locations_panel = QWidget()
        locations_layout = QVBoxLayout(locations_panel)

        # Add header
        header_label = QLabel("Visited Locations")
        header_label.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        locations_layout.addWidget(header_label)

        # Create locations list
        self.locations_list = QListWidget()
        self.locations_list.setMaximumHeight(200)
        self.locations_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        self.locations_list.itemClicked.connect(self.show_location_details)
        locations_layout.addWidget(self.locations_list)

        # Create the location details panel
        details_panel = QScrollArea()
        details_panel.setWidgetResizable(True)
        details_panel.setFrameShape(QFrame.Shape.NoFrame)

        self.location_details_widget = QWidget()
        self.location_details_layout = QVBoxLayout(self.location_details_widget)

        # Add a placeholder label
        placeholder = QLabel("Select a location to view details")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.location_details_layout.addWidget(placeholder)

        details_panel.setWidget(self.location_details_widget)

        # Add panels to the splitter
        splitter.addWidget(locations_panel)
        splitter.addWidget(details_panel)

        # Set initial sizes
        splitter.setSizes([150, 350])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def create_memories_tab(self):
        """Create the memories tab for narrative memory browsing"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Create the memory categories panel
        categories_panel = QWidget()
        categories_layout = QVBoxLayout(categories_panel)

        # Add header
        header_label = QLabel("Memory Categories")
        header_label.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        categories_layout.addWidget(header_label)

        # Create categories list
        self.memory_categories_list = QListWidget()
        self.memory_categories_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)

        # Add standard memory categories
        memory_categories = [
            "World Facts",
            "Character Development",
            "Relationships",
            "Plot Developments",
            "Player Decisions",
            "Environment Details",
            "Conversation Details",
            "New NPCs",
            "New Locations",
            "New Items",
            "New Quests"
        ]

        for category in memory_categories:
            self.memory_categories_list.addItem(category)

        self.memory_categories_list.itemClicked.connect(self.show_memory_category)
        categories_layout.addWidget(self.memory_categories_list)

        # Create the memory entries panel
        entries_panel = QWidget()
        entries_layout = QVBoxLayout(entries_panel)

        # Add header
        self.memory_entries_header = QLabel("Select a category")
        self.memory_entries_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        entries_layout.addWidget(self.memory_entries_header)

        # Create entries list
        self.memory_entries_list = QListWidget()
        self.memory_entries_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        entries_layout.addWidget(self.memory_entries_list)

        # Add panels to the splitter
        splitter.addWidget(categories_panel)
        splitter.addWidget(entries_panel)

        # Set initial sizes
        splitter.setSizes([150, 350])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def create_inventory_tab(self):
        """Create the inventory tab with player items"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Create the inventory list panel
        inventory_panel = QWidget()
        inventory_layout = QVBoxLayout(inventory_panel)

        # Add header
        header_label = QLabel("Inventory")
        header_label.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-weight: bold; font-size: 14px;")
        inventory_layout.addWidget(header_label)

        # Character stats
        self.character_stats = QLabel("Loading character stats...")
        self.character_stats.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 10px;
            color: #3A1E64;
        """)
        inventory_layout.addWidget(self.character_stats)

        # Create inventory list
        self.inventory_list = QListWidget()
        self.inventory_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid #E1D4F2;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_COLOR};
                color: white;
            }}
        """)
        self.inventory_list.itemClicked.connect(self.show_item_details)
        inventory_layout.addWidget(self.inventory_list)

        # Create the item details panel
        details_panel = QScrollArea()
        details_panel.setWidgetResizable(True)
        details_panel.setFrameShape(QFrame.Shape.NoFrame)

        self.item_details_widget = QWidget()
        self.item_details_layout = QVBoxLayout(self.item_details_widget)

        # Add a placeholder label
        placeholder = QLabel("Select an item to view details")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.item_details_layout.addWidget(placeholder)

        details_panel.setWidget(self.item_details_widget)

        # Add panels to the splitter
        splitter.addWidget(inventory_panel)
        splitter.addWidget(details_panel)

        # Set initial sizes
        splitter.setSizes([200, 300])

        # Add the splitter to the layout
        layout.addWidget(splitter)

        return tab

    def update_journal(self, game_state, detect_changes=True):
        """Update the journal with the latest game state"""
        self.game_state = game_state

        if not self.game_state:
            return

        # Record the current time for highlighting
        current_time = time.time()
        time_since_last_update = current_time - self.last_update_time
        self.last_update_time = current_time

        # Only detect changes if enough time has passed and it's requested
        detect_changes = detect_changes and time_since_last_update > 5  # 5 seconds threshold

        # Clear the highlight list if we're detecting changes
        if detect_changes:
            self.updated_items = []

        # Update quests tab
        self.update_quests_tab(detect_changes)

        # Update NPCs tab
        self.update_npcs_tab(detect_changes)

        # Update locations tab
        self.update_locations_tab(detect_changes)

        # Update inventory tab
        self.update_inventory_tab(detect_changes)

        # Start the highlight timer if we have updates
        if self.updated_items and detect_changes:
            self.highlight_timer.start(10000)  # Clear highlights after 10 seconds

    def update_quests_tab(self, detect_changes=True):
        """Update the quests tab with the latest quest information"""
        if not self.game_state:
            return

        # Store the currently selected item to restore selection
        selected_active = self.active_quests_list.currentItem()
        selected_active_text = selected_active.text() if selected_active else None

        selected_completed = self.completed_quests_list.currentItem()
        selected_completed_text = selected_completed.text() if selected_completed else None

        # Clear the lists
        self.active_quests_list.clear()
        self.completed_quests_list.clear()

        # Get player character
        pc_id = list(self.game_state['player_characters'].keys())[0]
        pc = self.game_state['player_characters'][pc_id]

        # Get all quests
        for quest_id in pc['quests']:
            if quest_id in self.game_state['quests']:
                quest = self.game_state['quests'][quest_id]

                # Create list item
                quest_text = quest['name']
                quest_item = QListWidgetItem(quest_text)

                # Set tooltip with short description
                quest_item.setToolTip(quest['description'])

                # Set data for referencing
                quest_item.setData(Qt.ItemDataRole.UserRole, quest_id)

                # Check if this quest has changed status recently
                if detect_changes:
                    quest_key = f"quest:{quest_id}"
                    old_status = getattr(self, f"old_quest_status_{quest_id}", None)
                    current_status = quest['status']

                    if old_status is not None and old_status != current_status:
                        self.updated_items.append(quest_key)

                    # Store current status for future comparison
                    setattr(self, f"old_quest_status_{quest_id}", current_status)

                # Add to appropriate list based on status
                if quest['status'] == "completed":
                    self.completed_quests_list.addItem(quest_item)
                    # If it was recently completed, highlight it
                    if f"quest:{quest_id}" in self.updated_items:
                        quest_item.setBackground(QBrush(QColor("#AED581")))  # Light green
                        quest_item.setForeground(QBrush(QColor("#33691E")))  # Dark green

                        # Make it bold to stand out
                        font = quest_item.font()
                        font.setBold(True)
                        quest_item.setFont(font)
                else:
                    # Check if this is the current quest
                    is_current = quest_id == self.game_state['game_info']['current_quest']

                    # Add visual indicator for current quest
                    if is_current:
                        quest_item.setText("► " + quest_text)
                        quest_item.setForeground(QBrush(QColor(self.HIGHLIGHT_COLOR)))

                        # Make it bold
                        font = quest_item.font()
                        font.setBold(True)
                        quest_item.setFont(font)

                    self.active_quests_list.addItem(quest_item)

                    # Highlight updated quests
                    if f"quest:{quest_id}" in self.updated_items and not is_current:
                        quest_item.setBackground(QBrush(QColor("#BBDEFB")))  # Light blue

        # Check if we had a selection and restore it
        if selected_active_text:
            for i in range(self.active_quests_list.count()):
                item = self.active_quests_list.item(i)
                if selected_active_text in item.text():
                    self.active_quests_list.setCurrentItem(item)
                    self.show_quest_details(item)
                    break

        if selected_completed_text:
            for i in range(self.completed_quests_list.count()):
                item = self.completed_quests_list.item(i)
                if selected_completed_text in item.text():
                    self.completed_quests_list.setCurrentItem(item)
                    self.show_quest_details(item)
                    break

    def update_npcs_tab(self, detect_changes=True):
        """Update the NPCs tab with the latest NPC information"""
        if not self.game_state:
            return

        # Store the currently selected item to restore selection
        selected_npc = self.npcs_list.currentItem()
        selected_npc_text = selected_npc.text() if selected_npc else None

        # Clear the list
        self.npcs_list.clear()

        # Get all NPCs
        if 'npcs' in self.game_state and self.game_state['npcs']:
            for npc_id, npc in self.game_state['npcs'].items():
                # Skip if name is missing or empty
                if 'name' not in npc or not npc['name']:
                    continue

                # Create list item with disposition indicator
                if 'disposition' in npc:
                    if npc['disposition'] == "friendly":
                        prefix = "🟢 "  # Green for friendly
                    elif npc['disposition'] == "hostile":
                        prefix = "🔴 "  # Red for hostile
                    elif npc['disposition'] == "mysterious":
                        prefix = "❓ "  # Question mark for mysterious
                    else:
                        prefix = "⚪ "  # White for neutral
                else:
                    prefix = "⚪ "  # Default

                # Create item
                npc_item = QListWidgetItem(f"{prefix}{npc['name']}")

                # Set tooltip
                if 'description' in npc:
                    npc_item.setToolTip(npc['description'])

                # Set data for referencing
                npc_item.setData(Qt.ItemDataRole.UserRole, npc_id)

                # Check if this is a new NPC
                if detect_changes:
                    # Check if this NPC was recently added to memory
                    for memory_item in self.game_state['narrative_memory'].get('new_npcs', []):
                        if npc['name'].lower() in memory_item.lower():
                            self.updated_items.append(f"npc:{npc_id}")
                            break

                    # Also check relationships for updates
                    old_relationships = getattr(self, f"old_npc_relationships_{npc_id}", {})
                    current_relationships = npc.get('relationships', {})

                    if old_relationships != current_relationships:
                        self.updated_items.append(f"npc:{npc_id}")

                    # Store current relationships for future comparison
                    setattr(self, f"old_npc_relationships_{npc_id}", current_relationships.copy())

                # Add to list
                self.npcs_list.addItem(npc_item)

                # Highlight new NPCs
                if f"npc:{npc_id}" in self.updated_items:
                    npc_item.setBackground(QBrush(QColor("#BBDEFB")))  # Light blue

                    # Make it bold
                    font = npc_item.font()
                    font.setBold(True)
                    npc_item.setFont(font)

        # Sort NPCs alphabetically but keep highlighted ones at the top
        self.npcs_list.sortItems()

        # Check if we had a selection and restore it
        if selected_npc_text:
            for i in range(self.npcs_list.count()):
                item = self.npcs_list.item(i)
                if selected_npc_text in item.text():
                    self.npcs_list.setCurrentItem(item)
                    self.show_npc_details(item)
                    break

    def update_locations_tab(self, detect_changes=True):
        """Update the locations tab with the latest location information"""
        if not self.game_state:
            return

        # Store the currently selected item to restore selection
        selected_location = self.locations_list.currentItem()
        selected_location_text = selected_location.text() if selected_location else None

        # Clear the list
        self.locations_list.clear()

        # Current location for comparison
        current_loc_id = self.game_state['game_info']['current_location']

        # Get all visited locations
        for loc_id, loc in self.game_state['locations'].items():
            if loc['visited']:
                # Create list item
                is_current = loc_id == current_loc_id

                # Add visual indicator for current location
                if is_current:
                    location_item = QListWidgetItem(f"▶ {loc['name']}")
                    location_item.setForeground(QBrush(QColor(self.HIGHLIGHT_COLOR)))

                    # Make it bold
                    font = location_item.font()
                    font.setBold(True)
                    location_item.setFont(font)
                else:
                    location_item = QListWidgetItem(loc['name'])

                # Set tooltip
                location_item.setToolTip(loc['description'])

                # Set data for referencing
                location_item.setData(Qt.ItemDataRole.UserRole, loc_id)

                # Check if this is a new location or if we've moved here
                if detect_changes:
                    # Check for new locations
                    for memory_item in self.game_state['narrative_memory'].get('new_locations', []):
                        if loc['name'].lower() in memory_item.lower():
                            self.updated_items.append(f"location:{loc_id}")
                            break

                    # Check if we've moved here
                    old_location = getattr(self, "old_current_location", None)
                    if old_location != current_loc_id and loc_id == current_loc_id:
                        self.updated_items.append(f"location:{loc_id}")

                    # Check for new connections
                    old_connections = getattr(self, f"old_location_connections_{loc_id}", [])
                    if set(old_connections) != set(loc['connected_to']):
                        self.updated_items.append(f"location:{loc_id}")

                    # Store current connections for future comparison
                    setattr(self, f"old_location_connections_{loc_id}", loc['connected_to'].copy())

                # Add to list
                self.locations_list.addItem(location_item)

                # Highlight new locations
                if f"location:{loc_id}" in self.updated_items and not is_current:
                    location_item.setBackground(QBrush(QColor("#BBDEFB")))  # Light blue

        # Store current location for future comparison
        if detect_changes:
            setattr(self, "old_current_location", current_loc_id)

        # Check if we had a selection and restore it
        if selected_location_text:
            for i in range(self.locations_list.count()):
                item = self.locations_list.item(i)
                if selected_location_text in item.text():
                    self.locations_list.setCurrentItem(item)
                    self.show_location_details(item)
                    break

    def update_inventory_tab(self, detect_changes=True):
        """Update the inventory tab with the latest player items"""
        if not self.game_state:
            return

        # Store the currently selected item to restore selection
        selected_item = self.inventory_list.currentItem()
        selected_item_text = selected_item.text() if selected_item else None

        # Clear the list
        self.inventory_list.clear()

        # Get player character
        pc_id = list(self.game_state['player_characters'].keys())[0]
        pc = self.game_state['player_characters'][pc_id]

        # Update character stats
        self.character_stats.setText(
            f"<b>{pc['name']}</b> - Level {pc['level']} {pc['race']} {pc['class']}<br>"
            f"Health: {pc['health']}/{pc['max_health']} | Gold: {pc['gold']}"
        )

        # Get inventory items
        old_inventory = getattr(self, "old_player_inventory", [])
        current_inventory = pc['inventory']

        # Track new items
        new_items = []
        if detect_changes and old_inventory:
            new_items = [item for item in current_inventory if item not in old_inventory]

        # Store current inventory for future comparison
        if detect_changes:
            setattr(self, "old_player_inventory", current_inventory.copy())

        # Add each inventory item
        for item_name in pc['inventory']:
            inventory_item = QListWidgetItem(item_name)

            # Look for item details if available
            if 'items' in self.game_state:
                for item_id, item_data in self.game_state['items'].items():
                    if item_data['name'] == item_name:
                        # Set tooltip
                        inventory_item.setToolTip(item_data['description'])

                        # Set data for referencing
                        inventory_item.setData(Qt.ItemDataRole.UserRole, item_id)
                        break

            # Add to list
            self.inventory_list.addItem(inventory_item)

            # Highlight new items
            if item_name in new_items:
                inventory_item.setBackground(QBrush(QColor("#BBDEFB")))  # Light blue

                # Make it bold
                font = inventory_item.font()
                font.setBold(True)
                inventory_item.setFont(font)

        # Check if we had a selection and restore it
        if selected_item_text:
            for i in range(self.inventory_list.count()):
                item = self.inventory_list.item(i)
                if selected_item_text == item.text():
                    self.inventory_list.setCurrentItem(item)
                    self.show_item_details(item)
                    break

    def show_quest_details(self, item):
        """Show details for the selected quest"""
        if not self.game_state or not item:
            return

        # Clear the details panel
        self.clear_widget_layout(self.quest_details_layout)

        # Get the quest ID
        quest_id = item.data(Qt.ItemDataRole.UserRole)

        if quest_id not in self.game_state['quests']:
            return

        quest = self.game_state['quests'][quest_id]

        # Create the details view
        # Quest header
        quest_header = QLabel(quest['name'])
        quest_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-size: 16px; font-weight: bold;")
        self.quest_details_layout.addWidget(quest_header)

        # Status indicator
        status_color = "#4CAF50" if quest['status'] == "completed" else "#FFC107"  # Green or amber
        status_text = f"Status: <span style='color: {status_color}; font-weight: bold;'>{quest['status'].title()}</span>"
        status_label = QLabel(status_text)
        status_label.setTextFormat(Qt.TextFormat.RichText)
        self.quest_details_layout.addWidget(status_label)

        # Description
        description_label = QLabel("Description:")
        description_label.setStyleSheet("font-weight: bold;")
        self.quest_details_layout.addWidget(description_label)

        description_text = QTextEdit()
        description_text.setReadOnly(True)
        description_text.setMaximumHeight(100)
        description_text.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        description_text.setText(quest['description'])
        self.quest_details_layout.addWidget(description_text)

        # Quest giver
        giver_label = QLabel(f"Given by: {quest['giver']}")
        self.quest_details_layout.addWidget(giver_label)

        # Difficulty
        difficulty_label = QLabel(f"Difficulty: {quest['difficulty']}")
        self.quest_details_layout.addWidget(difficulty_label)

        # Time sensitivity
        time_label = QLabel(f"Time Sensitive: {'Yes' if quest['time_sensitive'] else 'No'}")
        self.quest_details_layout.addWidget(time_label)

        # Steps
        steps_label = QLabel("Steps:")
        steps_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.quest_details_layout.addWidget(steps_label)

        steps_list = QListWidget()
        steps_list.setMaximumHeight(150)
        steps_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
            }}
        """)

        for step in quest['steps']:
            step_text = f"{'✓' if step.get('completed', False) else '□'} {step['description']}"
            step_item = QListWidgetItem(step_text)

            # Style completed steps
            if step.get('completed', False):
                step_item.setForeground(QBrush(QColor("#4CAF50")))  # Green for completed

                # Strike through completed steps
                font = step_item.font()
                font.setStrikeOut(True)
                step_item.setFont(font)

            steps_list.addItem(step_item)

        self.quest_details_layout.addWidget(steps_list)

        # Related memory entries
        memory_entries = []

        # Check memory for mentions of this quest
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if quest['name'].lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Journal Entries:")
            memory_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.quest_details_layout.addWidget(memory_label)

            memory_text = QTextEdit()
            memory_text.setReadOnly(True)
            memory_text.setStyleSheet(f"""
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            """)

            memory_content = ""
            for entry in memory_entries:
                memory_content += f"• {entry}\n"

            memory_text.setText(memory_content)
            self.quest_details_layout.addWidget(memory_text)

        # Add some spacing at the bottom
        self.quest_details_layout.addStretch()

    def show_npc_details(self, item):
        """Show details for the selected NPC"""
        if not self.game_state or not item:
            return

        # Clear the details panel
        self.clear_widget_layout(self.npc_details_layout)

        # Get the NPC ID
        npc_id = item.data(Qt.ItemDataRole.UserRole)

        if npc_id not in self.game_state['npcs']:
            return

        npc = self.game_state['npcs'][npc_id]

        # Create the details view
        # NPC header
        npc_header = QLabel(npc['name'])
        npc_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-size: 16px; font-weight: bold;")
        self.npc_details_layout.addWidget(npc_header)

        # Basic info
        race_label = QLabel(f"Race: {npc['race']}")
        self.npc_details_layout.addWidget(race_label)

        disposition_label = QLabel(f"Disposition: {npc['disposition']}")
        self.npc_details_layout.addWidget(disposition_label)

        # Location
        location_name = "Unknown"
        if npc['location'] in self.game_state['locations']:
            location_name = self.game_state['locations'][npc['location']]['name']

        location_label = QLabel(f"Current Location: {location_name}")
        self.npc_details_layout.addWidget(location_label)

        # Description
        description_label = QLabel("Description:")
        description_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.npc_details_layout.addWidget(description_label)

        description_text = QTextEdit()
        description_text.setReadOnly(True)
        description_text.setMaximumHeight(100)
        description_text.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        description_text.setText(npc['description'])
        self.npc_details_layout.addWidget(description_text)

        # Motivation
        motivation_label = QLabel("Motivation:")
        motivation_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.npc_details_layout.addWidget(motivation_label)

        motivation_text = QTextEdit()
        motivation_text.setReadOnly(True)
        motivation_text.setMaximumHeight(80)
        motivation_text.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        motivation_text.setText(npc['motivation'])
        self.npc_details_layout.addWidget(motivation_text)

        # Dialogue style
        dialogue_label = QLabel(f"Dialogue Style: {npc['dialogue_style']}")
        self.npc_details_layout.addWidget(dialogue_label)

        # Relationships
        if npc['relationships']:
            relationships_label = QLabel("Relationships:")
            relationships_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.npc_details_layout.addWidget(relationships_label)

            relationships_list = QListWidget()
            relationships_list.setMaximumHeight(100)
            relationships_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for person, relationship in npc['relationships'].items():
                relationships_list.addItem(f"{person}: {relationship}")

            self.npc_details_layout.addWidget(relationships_list)

        # Knowledge
        if npc['knowledge']:
            knowledge_label = QLabel("Knowledge:")
            knowledge_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.npc_details_layout.addWidget(knowledge_label)

            knowledge_list = QListWidget()
            knowledge_list.setMaximumHeight(100)
            knowledge_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for knowledge_item in npc['knowledge']:
                knowledge_list.addItem(knowledge_item)

            self.npc_details_layout.addWidget(knowledge_list)

        # Related memory entries
        memory_entries = []

        # Check memory for mentions of this NPC
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if npc['name'].lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Journal Entries:")
            memory_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.npc_details_layout.addWidget(memory_label)

            memory_text = QTextEdit()
            memory_text.setReadOnly(True)
            memory_text.setStyleSheet(f"""
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            """)

            memory_content = ""
            for entry in memory_entries:
                memory_content += f"• {entry}\n"

            memory_text.setText(memory_content)
            self.npc_details_layout.addWidget(memory_text)

        # Add some spacing at the bottom
        self.npc_details_layout.addStretch()

    def show_location_details(self, item):
        """Show details for the selected location"""
        if not self.game_state or not item:
            return

        # Clear the details panel
        self.clear_widget_layout(self.location_details_layout)

        # Get the location ID
        loc_id = item.data(Qt.ItemDataRole.UserRole)

        if loc_id not in self.game_state['locations']:
            return

        location = self.game_state['locations'][loc_id]

        # Create the details view
        # Location header
        location_header = QLabel(location['name'])
        location_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-size: 16px; font-weight: bold;")
        self.location_details_layout.addWidget(location_header)

        # Current location indicator
        if loc_id == self.game_state['game_info']['current_location']:
            current_label = QLabel("You are currently here")
            current_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.location_details_layout.addWidget(current_label)

        # Description
        description_label = QLabel("Description:")
        description_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.location_details_layout.addWidget(description_label)

        description_text = QTextEdit()
        description_text.setReadOnly(True)
        description_text.setMaximumHeight(100)
        description_text.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        description_text.setText(location['description'])
        self.location_details_layout.addWidget(description_text)

        # Ambience
        ambience_label = QLabel("Ambience:")
        ambience_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.location_details_layout.addWidget(ambience_label)

        ambience_text = QTextEdit()
        ambience_text.setReadOnly(True)
        ambience_text.setMaximumHeight(80)
        ambience_text.setStyleSheet(f"""
            background-color: white;
            border: 1px solid {self.ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        ambience_text.setText(location['ambience'])
        self.location_details_layout.addWidget(ambience_text)

        # NPCs present
        if location['npcs_present']:
            npcs_label = QLabel("NPCs Present:")
            npcs_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.location_details_layout.addWidget(npcs_label)

            npcs_list = QListWidget()
            npcs_list.setMaximumHeight(100)
            npcs_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for npc_id in location['npcs_present']:
                if npc_id in self.game_state['npcs']:
                    npc = self.game_state['npcs'][npc_id]
                    npcs_list.addItem(f"{npc['name']} - {npc['disposition']}")

            self.location_details_layout.addWidget(npcs_list)

        # Connected locations
        if location['connected_to']:
            connected_label = QLabel("Connected Locations:")
            connected_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.location_details_layout.addWidget(connected_label)

            connected_list = QListWidget()
            connected_list.setMaximumHeight(100)
            connected_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for connected_id in location['connected_to']:
                if connected_id in self.game_state['locations']:
                    connected_name = self.game_state['locations'][connected_id]['name']
                    connected_list.addItem(connected_name)

            self.location_details_layout.addWidget(connected_list)

        # Points of interest
        if location['points_of_interest']:
            poi_label = QLabel("Points of Interest:")
            poi_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.location_details_layout.addWidget(poi_label)

            poi_list = QListWidget()
            poi_list.setMaximumHeight(100)
            poi_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for poi in location['points_of_interest']:
                # Format the POI name nicely
                poi_name = poi.replace('_', ' ').title()
                poi_list.addItem(poi_name)

            self.location_details_layout.addWidget(poi_list)

        # Available quests
        if location['available_quests']:
            quests_label = QLabel("Available Quests:")
            quests_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.location_details_layout.addWidget(quests_label)

            quests_list = QListWidget()
            quests_list.setMaximumHeight(100)
            quests_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
            """)

            for quest_id in location['available_quests']:
                if quest_id in self.game_state['quests']:
                    quest = self.game_state['quests'][quest_id]
                    quests_list.addItem(f"{quest['name']} - {quest['status']}")

            self.location_details_layout.addWidget(quests_list)

        # Related memory entries
        memory_entries = []

        # Check memory for mentions of this location
        for category, items in self.game_state['narrative_memory'].items():
            for item in items:
                if location['name'].lower() in item.lower():
                    memory_entries.append(item)

        if memory_entries:
            memory_label = QLabel("Journal Entries:")
            memory_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.location_details_layout.addWidget(memory_label)

            memory_text = QTextEdit()
            memory_text.setReadOnly(True)
            memory_text.setStyleSheet(f"""
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            """)

            memory_content = ""
            for entry in memory_entries:
                memory_content += f"• {entry}\n"

            memory_text.setText(memory_content)
            self.location_details_layout.addWidget(memory_text)

        # Add travel button if not current location
        if loc_id != self.game_state['game_info']['current_location']:
            # Check if the location is directly connected to current location
            current_loc = self.game_state['locations'][self.game_state['game_info']['current_location']]
            can_travel = loc_id in current_loc['connected_to']

            travel_button = QPushButton("Travel Here")
            travel_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.ACCENT_COLOR};
                    color: white;
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.HIGHLIGHT_COLOR};
                }}
                QPushButton:disabled {{
                    background-color: #BDBDBD;
                    color: #757575;
                }}
            """)

            if not can_travel:
                travel_button.setDisabled(True)
                travel_button.setToolTip("Not directly connected to your current location")

            travel_button.clicked.connect(lambda: self.travel_to_location(loc_id))
            self.location_details_layout.addWidget(travel_button)

        # Add some spacing at the bottom
        self.location_details_layout.addStretch()

    def show_item_details(self, item):
        """Show details for the selected inventory item"""
        if not self.game_state or not item:
            return

        # Clear the details panel
        self.clear_widget_layout(self.item_details_layout)

        item_name = item.text()
        item_id = item.data(Qt.ItemDataRole.UserRole)

        # Create the details view
        # Item header
        item_header = QLabel(item_name)
        item_header.setStyleSheet(f"color: {self.HIGHLIGHT_COLOR}; font-size: 16px; font-weight: bold;")
        self.item_details_layout.addWidget(item_header)

        # If we have item details
        item_data = None
        if 'items' in self.game_state and item_id in self.game_state['items']:
            item_data = self.game_state['items'][item_id]

        if item_data:
            # Description
            description_label = QLabel("Description:")
            description_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.item_details_layout.addWidget(description_label)

            description_text = QTextEdit()
            description_text.setReadOnly(True)
            description_text.setMaximumHeight(100)
            description_text.setStyleSheet(f"""
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            """)
            description_text.setText(item_data['description'])
            self.item_details_layout.addWidget(description_text)

            # Properties
            if 'properties' in item_data:
                properties_label = QLabel("Properties:")
                properties_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
                self.item_details_layout.addWidget(properties_label)

                properties_text = QTextEdit()
                properties_text.setReadOnly(True)
                properties_text.setMaximumHeight(80)
                properties_text.setStyleSheet(f"""
                    background-color: white;
                    border: 1px solid {self.ACCENT_COLOR};
                    border-radius: 5px;
                    padding: 5px;
                """)
                properties_text.setText(item_data['properties'])
                self.item_details_layout.addWidget(properties_text)
        else:
            # Simple info for items without detailed data
            info_text = QLabel("A basic item in your inventory.")
            self.item_details_layout.addWidget(info_text)

        # Related memory entries
        memory_entries = []

        # Check memory for mentions of this item
        for category, items in self.game_state['narrative_memory'].items():
            for memory_item in items:
                if item_name.lower() in memory_item.lower():
                    memory_entries.append(memory_item)

        if memory_entries:
            memory_label = QLabel("Journal Entries:")
            memory_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.item_details_layout.addWidget(memory_label)

            memory_text = QTextEdit()
            memory_text.setReadOnly(True)
            memory_text.setStyleSheet(f"""
                background-color: white;
                border: 1px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
            """)

            memory_content = ""
            for entry in memory_entries:
                memory_content += f"• {entry}\n"

            memory_text.setText(memory_content)
            self.item_details_layout.addWidget(memory_text)

        # Add some spacing at the bottom
        self.item_details_layout.addStretch()

    def show_memory_category(self, item):
        """Show memory entries for the selected category"""
        if not self.game_state or not item:
            return

        # Clear the entries list
        self.memory_entries_list.clear()

        # Get the category name
        category_name = item.text()

        # Update the header
        self.memory_entries_header.setText(category_name)

        # Map display name to memory category key
        category_map = {
            "World Facts": "world_facts",
            "Character Development": "character_development",
            "Relationships": "relationships",
            "Plot Developments": "plot_developments",
            "Player Decisions": "player_decisions",
            "Environment Details": "environment_details",
            "Conversation Details": "conversation_details",
            "New NPCs": "new_npcs",
            "New Locations": "new_locations",
            "New Items": "new_items",
            "New Quests": "new_quests"
        }

        # Get the category key
        category_key = category_map.get(category_name, "")

        # Add entries to the list
        if category_key in self.game_state['narrative_memory']:
            for entry in self.game_state['narrative_memory'][category_key]:
                self.memory_entries_list.addItem(entry)

    def travel_to_location(self, location_id):
        """Travel to the specified location and update the game state"""
        if not self.game_state or location_id not in self.game_state['locations']:
            return

        # Set current location
        self.game_state['game_info']['current_location'] = location_id

        # Mark location as visited
        self.game_state['locations'][location_id]['visited'] = True

        # Highlight the change
        self.updated_items.append(f"location:{location_id}")

        # Update the journal
        self.update_journal(self.game_state, True)

        # Emit a signal for the main GUI to handle
        if hasattr(self.parent(), "handle_journal_travel"):
            self.parent().handle_journal_travel(location_id)

    def clear_widget_layout(self, layout):
        """Clear all widgets from a layout"""
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clear_widget_layout(item.layout())

    def clear_highlights(self):
        """Clear all highlights from items"""
        # Clear highlighted items in quests tab
        for i in range(self.active_quests_list.count()):
            item = self.active_quests_list.item(i)
            item.setBackground(QBrush())

        for i in range(self.completed_quests_list.count()):
            item = self.completed_quests_list.item(i)
            item.setBackground(QBrush())

        # Clear highlighted items in NPCs tab
        for i in range(self.npcs_list.count()):
            item = self.npcs_list.item(i)
            if not "▶" in item.text():  # Don't remove highlights from current location
                item.setBackground(QBrush())
                # Reset font weight if it was set to bold
                font = item.font()
                font.setBold(False)
                item.setFont(font)

        # Clear highlighted items in locations tab
        for i in range(self.locations_list.count()):
            item = self.locations_list.item(i)
            if not "▶" in item.text():  # Don't remove highlights from current location
                item.setBackground(QBrush())

        # Clear highlighted items in inventory tab
        for i in range(self.inventory_list.count()):
            item = self.inventory_list.item(i)
            item.setBackground(QBrush())

            # Reset font weight
            font = item.font()
            font.setBold(False)
            item.setFont(font)

        # Clear the updated items list
        self.updated_items = []