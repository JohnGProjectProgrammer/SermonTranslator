"""
main.py - Entry point for the real-time sermon translator application.
Initializes all modules, starts the threads, and launches the GUI.
"""
import sys
from PyQt5.QtWidgets import QApplication
from asr import ASR
from translation import Translator
from logger import Logger
from gui import TranslatorGUI

def main():
    """Main function to start the real-time sermon translator."""
    # Initialize translator (for English <-> Arabic translation)
    translator = Translator()
    # Initialize logger (to log English transcripts/translations)
    logger = Logger()
    # Initialize ASR manager (speech recognition and translation system)
    asr_system = ASR(translator, logger)
    # Create the Qt application and GUI
    app = QApplication(sys.argv)
    gui = TranslatorGUI(asr_system)
    # Connect the ASR transcriber's output signal to the GUI display slot
    asr_system.transcriber_thread.new_text.connect(gui.display_text)
    # Start the ASR system (begin audio capture and transcription threads)
    asr_system.start()
    # Show the GUI in full-screen mode for presentation
    gui.showFullScreen()
    # Run the Qt event loop
    try:
        app.exec_()
    finally:
        # Ensure threads are stopped and resources are cleaned up on exit
        asr_system.stop()
        logger.close()

if __name__ == "__main__":
    main()
