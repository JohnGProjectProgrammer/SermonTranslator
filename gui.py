"""
gui.py - Module for the PyQt5 GUI that displays translated text in large font,
         with full-screen display and a toggle button for translation direction.
"""
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class TranslatorGUI(QMainWindow):
    """
    GUI for the real-time sermon translator.
    Displays translated text in a large font and provides a button to toggle translation direction.
    """
    def __init__(self, asr_manager):
        """
        Initialize the GUI.
        :param asr_manager: The ASR manager (with translator and threads) to control and receive text from.
        """
        super().__init__()
        self.asr_manager = asr_manager
        # Set up window
        self.setWindowTitle("Real-Time Sermon Translator")
        # Create central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        # Create label to display translated text
        self.label = QLabel("...", self)
        # Configure label appearance for large text display
        font = QFont("Arial", 32, QFont.Bold)  # large, bold text
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)  # initially center text
        self.label.setWordWrap(True)  # allow multiline text if needed
        layout.addWidget(self.label, 1)  # give label vertical stretch factor 1 (to use available space)
        # Create toggle button for translation direction
        self.toggle_button = QPushButton(self)
        # Initial mode is English->Arabic
        self.current_mode = "EN->AR"
        self.toggle_button.setText("Switch to AR->EN")
        # Connect button signal to toggle handler
        self.toggle_button.clicked.connect(self.toggle_translation_direction)
        layout.addWidget(self.toggle_button, 0, alignment=Qt.AlignCenter)
        # Optionally, set the window to full-screen mode by default.
        # (This can also be done in main.py after initializing the GUI).
        # self.showFullScreen()

    def toggle_translation_direction(self):
        """
        Toggle the translation direction between English->Arabic and Arabic->English.
        Updates the button text and informs the ASR manager of the change.
        """
        if self.current_mode == "EN->AR":
            # Switch to Arabic -> English mode
            self.current_mode = "AR->EN"
            self.toggle_button.setText("Switch to EN->AR")
            # Inform ASR manager to switch mode
            self.asr_manager.set_mode("AR->EN")
        else:
            # Switch to English -> Arabic mode
            self.current_mode = "EN->AR"
            self.toggle_button.setText("Switch to AR->EN")
            self.asr_manager.set_mode("EN->AR")

    def display_text(self, text: str):
        """
        Display the given translated text on the label in the GUI.
        This method is intended to be connected to the ASR transcriber's signal.
        """
        # If the output text is Arabic, you might adjust alignment or direction for better readability.
        # Here we simply update the text in the label.
        self.label.setText(text)
        # Optionally, adjust alignment based on language direction for readability.
        if self.current_mode == "EN->AR":
            # Arabic text (target) is right-to-left, align to right and top for readability
            self.label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        else:
            # English text (target) is left-to-right, align to left and top
            self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

    def keyPressEvent(self, event):
        """
        Handle key press events to allow exiting full-screen or closing.
        Pressing Escape will exit the application.
        """
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            # Pass other keys to base class (for default handling)
            super().keyPressEvent(event)
