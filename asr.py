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
    def __init__(self, segment_queue: queue.Queue, stop_event: threading.Event, samplerate: int = 16000, chunk_duration_sec: float = 0.5, silence_sec: float = 0.8, silence_threshold: float = 0.01):
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
        self.samplerate = samplerate

        self.segment_queue = segment_queue
        self.stop_event = stop_event
        self.silence_sec = silence_sec
        self.silence_threshold = silence_threshold
        
        #Internal buffer for accumulating audio data for current utterance
        self._current_buffer=[]
        self._silence_start_time = None
        self._audio_frame_queue = queue.Queue(maxsize=10)
        self.block_size = int(chunk_duration_sec * samplerate)
        self._stream_started = False
        self._stream = None

    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback function for the audio input stream (Microphone).
        It is called in a seperate thread by sounddevice for each audio block.
        """
        if status:
            print(f"Audio input status: {status}", flush=True)
        # Copy the data to avoid referencing the input buffer
        try:
            self._audio_frame_queue.put_nowait(indata.copy())
        except queue.Full:
            try:
                self._audio_frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._audio_frame_queue.put_nowait(indata.copy())
            except queue.Full:
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
                frame = self._audio_frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            audio_frame = np.array(frame).astype(np.float32).flatten()
            rms = np.sqrt(np.mean(audio_frame**2)) if audio_frame.size > 0 else 0.0
            current_time = time.time()
            if rms < self.silence_threshold:
                if self._silence_start_time is None:
                    self._silence_start_time = current_time
                if self._silence_start_time is not None and (current_time - self._silence_start_time) >= self.silence_sec and self._current_buffer:
                    segment = np.concatenate(self._current_buffer)
                    self._current_buffer = []
                    self._silence_start_time = None
                    # Put the completed audio segment into the segment queue for transcription
                    try:
                        self.segment_queue.put_nowait(segment)
                    except queue.Full:
                        print("Warning: transcription queue is full. Dropping segment.")
            else:
                # Audio frame has speech (above silence threshold)
                # Append to current buffer
                self._current_buffer.append(audio_frame)
                self._silence_start_time = None
        if self._stream and self._stream_started:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")

class ASRTranscriber(QThread):
    """
    Thread that consumes audio segments and performs speech-to-text using Faster-Whisper,
    then translates the text to the target language using the provided Translator.
    Emits the translated text to a Qt signal for display.
    """
    new_text = pyqtSignal(str)

    def __init__(self, segment_queue: queue.Queue, translator, logger, initial_mode: str = "EN->AR", model_size: str = "small"):
        """
        Initialize the ASR transcriber thread.
        :param segment_queue: Queue from which to read audio segments for transcription.
        :param translator: Translator instance for performing translations.
        :param logger: Logger instance for logging English text.
        :param initial_mode: Initial translation mode ("EN->AR" or "AR->EN").
        :param model_size: Size of the Whisper model to load (default "small").
        """
        super().__init__()
        self.segment_queue = segment_queue
        self.translator = translator
        self.logger = logger
        self.mode = initial_mode
        self.model_size = model_size
        self._model = None
        # Load the Whisper model in the run() to avoid blocking the main thread on initialization.

    def run(self):
        """Run the transcription and translation thread. Loads the ASR model and processes audio segments."""
        try:
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        except Exception as e:
            print(f"Failed to load Whisper model (size={self.model_size}): {e}")
            return
        while not self.isInterruptionRequested():
            try:
                segment = self.segment_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if segment is None:
                break
            # Perform speech recognition on the audio segment.
            try:
                language = "en" if self.mode == "EN->AR" else "ar"
                segments, info = self._model.transcribe(segment, language=language)
                # Collect the transcribed text from the segments generator
                transcribed_text = "".join([seg.text for seg in segments]).strip()
            except Exception as e:
                print(f"Transcription failed: {e}")
                transcribed_text = ""
            if not transcribed_text:
                continue
            if self.mode == "EN->AR":
                translated_text = self.translator.translate_en_to_ar(transcribed_text)
                english_text_to_log = transcribed_text  # source was English
            else:
                translated_text = self.translator.translate_ar_to_en(transcribed_text)
                english_text_to_log = translated_text  # result is English
            # Emit the translated text for GUI display
            self.new_text.emit(translated_text if translated_text is not None else "")
            if english_text_to_log:
                self.logger.log(english_text_to_log)
        self._model = None

class ASR:
    """
    ASR manager class that ties together the audio capture and transcription threads.
    Provides methods to start/stop the threads and to change translation mode.
    """
    def __init__(self, translator, logger, model_size: str = "small"):
        """
        Initialize the ASR system with given translator and logger.
        :param translator: Translator instance for performing translations.
        :param logger: Logger instance for logging English text.
        :param model_size: Whisper model size to use for ASR (default "small").
        """
        self.segment_queue = queue.Queue(maxsize=5)
        self.stop_event = threading.Event()
        self.capture_thread = AudioCaptureThread(self.segment_queue, self.stop_event)
        self.transcriber_thread = ASRTranscriber(self.segment_queue, translator, logger, initial_mode="EN->AR", model_size=model_size)

    def start(self):
        """Start the audio capture and transcription threads."""
        self.transcriber_thread.start()
        self.capture_thread.start()

    def stop(self):
        """Stop the audio capture and transcription threads."""
        self.stop_event.set()
        self.capture_thread.join(timeout=5.0)
        # Send a sentinel None to the segment queue to ensure the transcriber thread can exit if waiting
        try:
            self.segment_queue.put_nowait(None)
        except queue.Full:
            try:
                self.segment_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.segment_queue.put_nowait(None)
            except Exception:
                pass
        self.transcriber_thread.requestInterruption()
        self.transcriber_thread.wait(5000)  # wait up to 5 seconds for clean exit

    def set_mode(self, mode: str):
        """
        Set the translation direction mode.
        :param mode: "EN->AR" for English-to-Arabic or "AR->EN" for Arabic-to-English.
        """
        if mode not in ("EN->AR", "AR->EN"):
            raise ValueError("Mode must be 'EN->AR' or 'AR->EN'.")
        self.transcriber_thread.mode = mode
        # (The audio capture is language-agnostic; we rely on the transcriber to handle language setting.)

       