"""
Campaign selection dialog for the AI Narrative RPG system.
Created to break circular dependency between memory_system.py and rpg_gui.py.
"""

import os
import time
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QInputDialog, QMessageBox
)

class CampaignSelectionDialog(QDialog):
    """Dialog for selecting or creating a campaign."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Campaign")
        self.resize(500, 400)
        self.new_campaign_requested = False
        self.new_campaign_name = ""

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

        delete_campaign_btn = QPushButton("Delete Campaign")
        delete_campaign_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5555;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FF3333;
                }
            """)
        delete_campaign_btn.clicked.connect(self.delete_selected_campaign)
        layout.addWidget(delete_campaign_btn)
        
        # Initialize campaigns list
        self.campaigns = []

    def set_campaigns(self, campaigns):
        """Set the list of available campaigns."""
        self.campaigns = campaigns
        self.campaign_list.clear()
        
        for campaign in self.campaigns:
            campaign_name = campaign.get("name", "Unknown Campaign")
            created_date = time.strftime("%Y-%m-%d", time.localtime(campaign.get("created", 0)))
            modified_date = time.strftime("%Y-%m-%d", time.localtime(campaign.get("last_modified", 0)))

            item = QListWidgetItem(f"{campaign_name} (Created: {created_date}, Last played: {modified_date})")
            self.campaign_list.addItem(item)

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

    def delete_selected_campaign(self):
        """Delete the selected campaign."""
        # Get selected campaign
        selected_item = self.campaign_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a campaign to delete.")
            return

        idx = self.campaign_list.row(selected_item)
        if 0 <= idx < len(self.campaigns):
            campaign_id = self.campaigns[idx].get("id")
            campaign_name = self.campaigns[idx].get("name", "Unknown Campaign")

            # Confirm deletion
            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the campaign '{campaign_name}'?\n\nThis will permanently delete all characters, locations, and game history associated with this campaign.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default is No to prevent accidental deletion
            )

            if confirm == QMessageBox.Yes:
                # Try to use parent's delete_campaign method if available
                parent = self.parent()
                if parent and hasattr(parent, 'delete_campaign'):
                    result = parent.delete_campaign(campaign_id)
                    
                    if result:
                        # Remove from list
                        self.campaign_list.takeItem(idx)
                        self.campaigns.pop(idx)
                        QMessageBox.information(self, "Campaign Deleted", f"Campaign '{campaign_name}' has been deleted.")
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to delete campaign '{campaign_name}'.")
                else:
                    QMessageBox.critical(self, "Error", "Delete functionality not available in this context.")

    def accept(self):
        """Override accept to validate selection."""
        if not self.selected_campaign_id and self.campaigns and not self.new_campaign_requested:
            # If nothing selected but campaigns exist, select the first one
            self.selected_campaign_id = self.campaigns[0].get("id")

        if self.selected_campaign_id or self.new_campaign_requested:
            super().accept()
        else:
            QMessageBox.warning(self, "No Campaign Selected",
                               "Please select a campaign or create a new one.")