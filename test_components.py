# test_components.py
def test_vector_store():
    """Test the vector store component."""
    from vector_store import VectorStore
    print("Testing Vector Store...")

    # Create instance
    vs = VectorStore("test")

    # Test basic operations
    test_text = "This is a test memory for the RPG system."
    memory_id = vs.store_memory(test_text, {"type": "test", "importance": 0.8})
    print(f"Stored memory with ID: {memory_id}")

    # Test search
    results = vs.search_similar("test memory RPG", top_k=1)
    print(f"Search results: {results}")

    print("Vector Store test complete.\n")


def test_card_manager():
    """Test the card manager component."""
    from card_manager import CardManager
    print("Testing Card Manager...")

    # Create instance
    cm = CardManager("test")

    # Create a character
    char_id = cm.create_card("character", "Test Character", {
        "description": "A test character for the RPG system.",
        "traits": {"strength": "medium", "intelligence": "high"},
        "inventory": ["sword", "potion"],
        "location": "test_location"
    })
    print(f"Created character with ID: {char_id}")

    # Get the character
    character = cm.get_card(char_id)
    print(f"Retrieved character: {character.name}")

    # Update the character
    cm.update_card(char_id, {"traits": {"strength": "high"}}, "test")
    character = cm.get_card(char_id)
    print(f"Updated character strength: {character.traits['strength']}")

    print("Card Manager test complete.\n")


def test_context_assembler():
    """Test the context assembler component."""
    from context_assembler import ContextAssembler
    from card_manager import CardManager
    from vector_store import VectorStore

    print("Testing Context Assembler...")

    # Create dependencies
    cm = CardManager("test")
    vs = VectorStore("test")

    # Create context assembler
    ca = ContextAssembler(cm, vs)

    # Test context assembly
    context = ca.assemble_context(
        "The player is exploring the forest.",
        [{"user": "I look around", "ai": "You see tall trees and undergrowth."}]
    )

    print(f"Generated context length: {len(context)} characters")
    print("First 100 characters of context:")
    print(context[:100] + "...")

    print("Context Assembler test complete.\n")


if __name__ == "__main__":
    print("=== Component Tests ===\n")
    test_vector_store()
    test_card_manager()
    test_context_assembler()

    print("All component tests completed!")