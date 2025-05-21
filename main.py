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
    translator = Translator()
    logger = Logger()
    asr_system = ASR(translator, logger)
    app = QApplication(sys.argv)
    gui = TranslatorGUI(asr_system)
    # Connect the ASR transcriber's output signal to the GUI display slot
    asr_system.transcriber_thread.new_text.connect(gui.display_text)
    asr_system.start()
    gui.showFullScreen()
    try:
        app.exec_()
    finally:
        asr_system.stop()
        logger.close()

if __name__ == "__main__":
    main()
