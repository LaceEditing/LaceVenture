import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton, QVBoxLayout, QWidget
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class RPGGameGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Memory-Enhanced RPG System")
        self.setGeometry(100, 100, 800, 600)

        # Main widget and layout
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # Game output display
        self.game_display = QTextEdit()
        self.game_display.setReadOnly(True)
        layout.addWidget(self.game_display)

        # User input field
        self.user_input = QLineEdit()
        layout.addWidget(self.user_input)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.process_input)
        layout.addWidget(self.send_button)

        # Set the central widget
        self.setCentralWidget(main_widget)

        # Initialize model and tokenizer
        self.initialize_model()

        # Game history/context
        self.game_context = "You are in a medieval fantasy world. The adventure begins in a small village called Riverdale."
        self.game_display.setText("Game Master: " + self.game_context)

    def initialize_model(self):
        """Initialize the LLM model and tokenizer."""
        try:
            model_name = "jondurbin/airoboros-m-7b-3.1.2"  # Could be configurable in settings

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)

            # Load with reduced precision for better performance
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto",
                torch_dtype=torch.float16,  # Use half precision
                load_in_8bit=True  # 8-bit quantization
            )

            self.game_display.append("\nSystem: Model loaded successfully.")
        except Exception as e:
            self.game_display.append(f"\nSystem Error: Failed to load model: {str(e)}")

    def process_input(self):
        """Process the player's input and generate a response."""
        user_text = self.user_input.text()
        if not user_text:
            return

        # Display user input
        self.game_display.append(f"\nPlayer: {user_text}")
        self.user_input.clear()

        # Prepare prompt with context
        full_prompt = f"{self.game_context}\n\nPlayer: {user_text}\n\nAI Game Master:"

        try:
            # Generate response
            inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True
            )

            # Extract and display response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            gm_response = response.split("AI Game Master:")[-1].strip()

            self.game_display.append(f"\nGame Master: {gm_response}")

            # Update context with this interaction
            self.game_context += f"\nPlayer: {user_text}\nGame Master: {gm_response}"

        except Exception as e:
            self.game_display.append(f"\nSystem Error: {str(e)}")


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RPGGameGUI()
    window.show()
    sys.exit(app.exec_())