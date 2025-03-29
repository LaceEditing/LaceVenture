# In your main.py or a new test_campaign.py file
from memory_system import MemorySystem


def create_test_campaign():
    """Create a simple test campaign with basic elements."""
    memory_system = MemorySystem(campaign_name="Test Campaign")

    # Initial setup data
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
            "characters": ["0"],  # Will be replaced with Old Wizard ID
            "location": "0",  # Will be replaced with Town Square ID
            "items": ["0"]  # Will be replaced with Magic Scroll ID
        }
    }

    # Create campaign
    memory_system.create_campaign("Test Campaign", initial_setup)
    print("Test campaign created successfully!")
    return memory_system


if __name__ == "__main__":
    create_test_campaign()