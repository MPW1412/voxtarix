import sounddevice as sd
import numpy as np
import whisper
import sys
import queue
import threading
import time
import argparse
import pyperclip
import re
from pynput import keyboard
import json
import configparser

class VoxtarixEngine:
    def __init__(self, device="cuda", language=None):
        config = configparser.ConfigParser()
        try:
            config.read('settings.conf')
            self.SAMPLE_RATE = config.getint('audio', 'sample_rate', fallback=16000)
            self.CHANNELS = config.getint('audio', 'channels', fallback=1)
            self.BLOCKSIZE = config.getint('audio', 'blocksize', fallback=1024)
            self.GAIN = config.getfloat('audio', 'gain', fallback=8.0)
            self.SILENCE_THRESHOLD = config.getfloat('audio', 'silence_threshold', fallback=0.15)
            self.SILENCE_DURATION = config.getfloat('audio', 'silence_duration', fallback=2.0)
            self.MIN_DURATION = config.getfloat('audio', 'min_duration', fallback=0.5)
            self.WARMUP_TIME = config.getfloat('audio', 'warmup_time', fallback=2.0)
            self.TYPE_DELAY = config.getfloat('audio', 'type_delay', fallback=0.01)
            model_name = config.get('whisper', 'model_name', fallback="medium")
        except Exception as e:
            print(f"Error reading config file: {e}. Using default values.", file=sys.stderr)
            model_name = "medium"

        self.model = whisper.load_model(model_name, device=device)
        self.language = language
        self.audio_queue = queue.Queue()
        self.use_clipboard = False
        self.use_typing = False
        self.should_terminate = False
        self.keyboard_controller = keyboard.Controller()
        self.stream = None
        self.processing_thread = None

        # Load commands from translation file
        with open("commands.json", "r") as f:
            commands_data = json.load(f)
        self.command_regexes = {}
        for command, lang_phrases in commands_data.items():
            phrases = lang_phrases.get(language or "en", [])
            if isinstance(phrases, str):
                phrases = [phrases]
            print(f"Debug: Command {command}, Language {language or 'en'}, Phrases: {phrases}", file=sys.stderr)
            self.command_regexes[command] = [self.compile_command_regex(phrase) for phrase in phrases]

    def compile_command_regex(self, phrase):
        words = phrase.split()
        pattern = r"^\s*" + r"[,\s.;:-]*".join(re.escape(word) for word in words) + r"\s*[.!?]?$"
        return re.compile(pattern, re.IGNORECASE)

    def audio_callback(self, indata, frames, time, status):
        amplified_data = indata[:, 0] * self.GAIN
        amplified_data = np.clip(amplified_data, -1.0, 1.0)
        self.audio_queue.put(amplified_data.copy())

    def process_audio(self):
        audio_buffer = np.array([], dtype=np.float32)
        silence_samples = 0
        silence_limit = int(self.SILENCE_DURATION * self.SAMPLE_RATE)
        min_samples = int(self.MIN_DURATION * self.SAMPLE_RATE)
        max_amplitude_seen = 0.0
        start_time = time.time()
        speech_started = False

        while not self.should_terminate:
            if time.time() - start_time < self.WARMUP_TIME:
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        break
                time.sleep(0.1)
                continue

            try:
                chunk = self.audio_queue.get(timeout=1)
                chunk_size = len(chunk)
                chunk_amplitude = np.max(np.abs(chunk))

                if chunk_amplitude >= self.SILENCE_THRESHOLD:
                    speech_started = True

                max_amplitude_seen = max(max_amplitude_seen, chunk_amplitude)
                audio_buffer = np.append(audio_buffer, chunk)

                if chunk_amplitude < self.SILENCE_THRESHOLD:
                    silence_samples += chunk_size
                    if silence_samples >= silence_limit and len(audio_buffer) >= min_samples and speech_started:
                        if max_amplitude_seen >= self.SILENCE_THRESHOLD:
                            self.transcribe_and_handle(audio_buffer)
                        audio_buffer = np.array([], dtype=np.float32)
                        silence_samples = 0
                        max_amplitude_seen = 0.0
                        speech_started = False
                else:
                    silence_samples = 0

            except queue.Empty:
                silence_samples += self.BLOCKSIZE
                if silence_samples >= silence_limit and len(audio_buffer) >= min_samples and speech_started:
                    if max_amplitude_seen >= self.SILENCE_THRESHOLD:
                        self.transcribe_and_handle(audio_buffer)
                    audio_buffer = np.array([], dtype=np.float32)
                    silence_samples = 0
                    max_amplitude_seen = 0.0
                    speech_started = False

    def transcribe_and_handle(self, audio_buffer):
        try:
            result = self.model.transcribe(
                audio_buffer,
                language=self.language,
                condition_on_previous_text=False
            )
            text = result["text"]
            if not text:
                print("[Empty]", flush=True)
                if self.use_clipboard:
                    print(f"Attempting to copy: '[Empty]' to clipboard", file=sys.stderr)
                    pyperclip.copy("[Empty]")
            else:
                command_recognized = self.handle_command(text)
                if not command_recognized:
                    print(text, flush=True)
                    if self.use_clipboard:
                        print(f"Attempting to copy: '{text}' to clipboard", file=sys.stderr)
                        pyperclip.copy(text)
                    if self.use_typing:
                        print(f"Attempting to type: '{text}'", file=sys.stderr)
                        for char in text:
                            try:
                                self.keyboard_controller.type(char)
                                time.sleep(self.TYPE_DELAY)
                            except ValueError:
                                print(f"Failed to type character: '{char}'", file=sys.stderr)
        except Exception as e:
            print(f"Whisper error: {e}", file=sys.stderr)

    def handle_command(self, text):
        print(f"Received text: '{text}'", file=sys.stderr)
        command_recognized = False
        for command, regexes in self.command_regexes.items():
            for regex in regexes:
                if regex.match(text):
                    print(f"Matched command: {command} with text: {text}", file=sys.stderr)
                    command_recognized = True
                    if command == "terminate":
                        print("Terminating program on voice command...", file=sys.stderr)
                        self.should_terminate = True
                    elif command == "clipboard_on":
                        self.use_clipboard = True
                        print("Clipboard enabled", file=sys.stderr)
                    elif command == "clipboard_off":
                        self.use_clipboard = False
                        print("Clipboard disabled", file=sys.stderr)
                    elif command == "typing_on":
                        self.use_typing = True
                        print("Typing enabled", file=sys.stderr)
                    elif command == "typing_off":
                        self.use_typing = False
                        print("Typing disabled", file=sys.stderr)
                    else:
                        if self.use_clipboard:
                            print(f"Attempting to copy: '{text}' to clipboard", file=sys.stderr)
                            pyperclip.copy(text)
                        if self.use_typing:
                            for char in text:
                                try:
                                    self.keyboard_controller.type(char)
                                    time.sleep(self.TYPE_DELAY)
                                except ValueError:
                                    pass
                    break
        return command_recognized

    def start(self):
        default_input_device = sd.default.device[0]
        if default_input_device is None:
            print("No default input device found! Please check microphone.", file=sys.stderr)
            sys.exit(1)
        dev = sd.query_devices(default_input_device)
        print(f"Selected device: {dev['name']}", file=sys.stderr)

        self.stream = sd.InputStream(
            device=default_input_device,
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            blocksize=self.BLOCKSIZE,
            callback=self.audio_callback,
            dtype='float32'
        )

        with self.stream:
            self.processing_thread = threading.Thread(target=self.process_audio, daemon=True)
            self.processing_thread.start()
            print("Aufnahme läuft... (Strg+C zum Beenden)", file=sys.stderr)
            try:
                while True:
                    if self.should_terminate:
                        self.keyboard_controller = None
                        self.stream.close()
                        sys.exit(0)
                    threading.Event().wait(0.1)
            except KeyboardInterrupt:
                print("Beende Aufnahme...", file=sys.stderr)
                self.keyboard_controller = None
            finally:
                try:
                    self.stream.close()
                except Exception as e:
                    print(f"Fehler beim Schließen des Streams: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transkribiere Sprache mit Whisper.")
    parser.add_argument("-c", "--clipboard", action="store_true", help="Schreibe transkribierten Text in die Zwischenablage")
    parser.add_argument("-t", "--type", action="store_true", help="Simuliere Tastatureingaben für den transkribierten Text")
    parser.add_argument("-l", "--language", type=str, default=None, help="Sprache für die Transkription (z.B. 'en', 'de')")
    args = parser.parse_args()

    engine = VoxtarixEngine(language=args.language)
    engine.use_clipboard = args.clipboard
    engine.use_typing = args.type
    engine.start()