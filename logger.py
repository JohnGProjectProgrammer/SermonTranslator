"""
logger.py - Module for logging transcripts and translations to disk.
"""
import os
import datetime

class Logger:
    """
    Logger class to record English transcripts or translations with timestamps.
    Logs are saved to timestamped text files for later use (e.g., summarization).
    """
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the logger by creating a new log file.
        The log file is placed in `log_dir` and named with the current date and time.
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        # Create a log file with a timestamp in the name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sermon_{timestamp}.txt"
        self.file_path = os.path.join(self.log_dir, filename)
        try:
            self.file = open(self.file_path, mode="w", encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Failed to open log file {self.file_path}: {e}")
        # Write a header line to the log file (optional)
        start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.file.write(f"Log started at {start_time}\n")
        self.file.flush()

    def log(self, text: str):
        """
        Log a line of text with a timestamp (in HH:MM:SS format).
        Only log if text is non-empty.
        """
        if not text:
            return
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            self.file.write(f"[{timestamp}] {text}\n")
            self.file.flush()
        except Exception as e:
            # In production, we might handle or print an error message.
            print(f"Logging error: {e}")

    def close(self):
        """Close the log file."""
        try:
            self.file.close()
        except Exception as e:
            print(f"Error closing log file: {e}")
