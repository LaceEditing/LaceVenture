# test_system.py
from memory_system import MemorySystem
from llm_interface import LLMInterface
from test_campaign import create_test_campaign  # Import from your existing file


def test_interactive_session():
    """Run an interactive test session with the memory system."""
    print("Loading memory system...")
    memory_system = MemorySystem()

    # Try to load existing campaign or create test one
    campaigns = memory_system.get_available_campaigns()
    if campaigns:
        print("\nAvailable campaigns:")
        for i, campaign in enumerate(campaigns):
            print(f"{i + 1}. {campaign['name']}")
        choice = input("\nEnter campaign number to load (or 'n' for new test campaign): ")

        if choice.lower() != 'n':
            try:
                index = int(choice) - 1
                memory_system.load_campaign(campaigns[index]["id"])
            except:
                print("Invalid choice. Creating new test campaign.")
                create_test_campaign()
        else:
            create_test_campaign()
    else:
        print("No campaigns found. Creating test campaign...")
        create_test_campaign()

    print("\n=== Test Interactive Session ===")
    print("Type 'exit' to end the session")

    while True:
        user_input = input("\nYOU: ")
        if user_input.lower() == 'exit':
            break

        response = memory_system.process_turn(user_input)
        print(f"\nAI: {response}")


if __name__ == "__main__":
    test_interactive_session()