"""
asr.py- Module for capturing audio from microphone and performing performing speech
recognition using Faster-Whisper (OpenAI Iteration).
Supports English and Arabic input, uses CPU (no GPU required), and streams audio via sounddevice.
"""
import queue
import threading
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from PyQt5.QtCore import QThread, pyqtSignal

class AudioCaptureThread(threading.Thread):
    """
    Thread that captures audio from the microphone and segments it into utterances based on silence detection.
    Segmented audio chunks are put into a queue for transcription.
    """
    def __init__(self, segment_queue: queue.Queue, stop_event: threading.Event, samplerate: int = 16000, chunk_duration_sec: float = 0.5, silence_sec: float = 0.8, silince_threshold: float = 0.01):
        """
        Initialize the audio capture thread.
        :param segment_queue: Queue to send completed audio segments (numpy arrays of audio samples) for transcription.
        :param stop_event: Event to signal the thread to stop capturing.
        :param samplerate: Sampling rate for audio capture (default 16kHz for Whisper model compatibility).
        :param chunk_duration_sec: Duration of audio (in seconds) per chunk for callback processing.
        :param silence_sec: Amount of continuous silence (in seconds) to consider an utterance boundary.
        :param silence_threshold: RMS amplitude threshold below which audio is considered silence.
        """
        super().__init__(daemon=True)
        self.segment_queue = segment_queue
        self.stop_event = stop_event
        self.sample_rate = samplerate
        self.silence_sec = silence_sec
        self.silience_threshold = silince_threshold
        #Internal buffer for accumulating audio data for current utterance
        self.current_buffer=[]
        # Time when silence started, None if currently in speech
        self._silence_start_time = None
        # A queue for audio frames from the callback
        self._audio_frame_queue = queue.Queue(maxsize=10)
        # Use a small block size for lower latency (optional)
        self.block_size = int(chunk_duration_sec * samplerate)
        # Flag to indicate if stream started successfully
        self._stream_started = False
        # Input audio stream (will be created in run)
        self._stream = None

    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback function for the audio input stream (Microphone).
        It is called in a seperate thread by sounddevice for each audio block.
        """
        if status:
            # If there's an input overflow or other issue, we can print a warning
            print(f"Audio input status: {status}", flush=True)
        # Copy the data to avoid referencing the input buffer
        try:
            # Put the audio frame into the queue, non-blocking (drop if queue is full to avoid stalling)
            self._audio_frame_queue.put_nowait(indata.copy())
        except queue.Full:
            # If frames are coming in faster than processing, drop the oldest
            try:
                self._audio_frame_queue.get_nowait()
            except queue.Empty:
                pass
            # Try again to put the frame
            try:
                self._audio_frame_queue.put_nowait(indata.copy())
            except queue.Full:
                # If still full, drop this frame
                pass
            
    def run(self):
        """Run the audio capture thread, reading microphone input and segmenting audio based on silence."""
        try:
            # Open the microphone input stream
            self._stream = sd.InputStream(channels=1, samplerate=self.samplerate, blocksize=self.block_size, callback=self.audio_callback)
            self._stream.start()
            self._stream_started = True
        except Exception as e:
            print(f"Failed to start audio stream: {e}")
            return
        # Process audio frames until stopped
        while not self.stop_event.is_set():
            try:
                # Get a frame of audio data (blocks until a frame is available or timeout)
                frame = self._audio_frame_queue.get(timeout=0.1)
            except queue.Empty:
                # No frame available in this interval, loop and check stop_event
                continue
            # Convert audio frame to numpy array of float32 if not already
            audio_frame = np.array(frame).astype(np.float32).flatten()
            # Compute RMS volume of this frame
            rms = np.sqrt(np.mean(audio_frame**2)) if audio_frame.size > 0 else 0.0
            current_time = time.time()
            if rms < self.silence_threshold:
                # Current frame is silent or below threshold
                if self._silence_start_time is None:
                    # Mark the start of a silence period
                    self._silence_start_time = current_time
                # If silence has lasted long enough and we have audio buffered
                if self._silence_start_time is not None and (current_time - self._silence_start_time) >= self.silence_sec and self._current_buffer:
                    # End of an utterance detected
                    segment = np.concatenate(self._current_buffer)
                    # Clear the current buffer for the next utterance
                    self._current_buffer = []
                    # Reset silence timer
                    self._silence_start_time = None
                    # Put the completed audio segment into the segment queue for transcription
                    try:
                        self.segment_queue.put_nowait(segment)
                    except queue.Full:
                        # If the transcription queue is full, drop the segment (to avoid backlog growth)
                        print("Warning: transcription queue is full. Dropping segment.")
            else:
                # Audio frame has speech (above silence threshold)
                # Append to current buffer
                self._current_buffer.append(audio_frame)
                # Reset silence timer since we are in speech
                self._silence_start_time = None
        # Outside of loop: stop event set, clean up
        if self._stream and self._stream_started:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")