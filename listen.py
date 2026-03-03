#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyaudio",
#   "openai",
#   "groq",
#   "pyperclip",
# ]
# ///


import argparse
import os
import sys
import tty
import termios
import threading
from datetime import datetime
from typing import Optional
from pathlib import Path
import tempfile
import wave
import array

import openai
import groq
import pyaudio
import pyperclip

# ____________________________________________________________________________________________

# Audio recording parameters
CHUNK = 1024  # Size of the audio chunk to process
FORMAT = pyaudio.paInt16  # Changed from paFloat32 to standard PCM format
CHANNELS = 1  # Number of audio channels (mono)
RATE = 16000  # Changed to 16000
SILENCE_THRESHOLD = 800  # Amplitude threshold for speech detection display

# ____________________________________________________________________________________________

class SuppressStderr:
    """Context manager to suppress stderr output (used to silence ALSA/JACK warnings)."""
    def __enter__(self):
        self.null_fd = os.open(os.devnull, os.O_RDWR)
        self.save_fd = os.dup(2)
        os.dup2(self.null_fd, 2)

    def __exit__(self, *_):
        os.dup2(self.save_fd, 2)
        os.close(self.null_fd)
        os.close(self.save_fd)

# ____________________________________________________________________________________________

class InteractiveRecorder:
    """Interactive recorder with manual pause/resume control via keypresses."""

    RECORDING = "RECORDING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"

    def __init__(self, transcriber: "Transcriber", language: Optional[str]):
        with SuppressStderr():
            self.p = pyaudio.PyAudio()
        self.state = self.RECORDING
        self.lock = threading.Lock()
        self.old_term_settings = termios.tcgetattr(sys.stdin)
        self.transcriber = transcriber
        self.language = language
        self.text_segments = []
        self.session_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.segment_counter = 0

    def _set_state(self, new_state: str) -> None:
        with self.lock:
            self.state = new_state

    def _get_state(self) -> str:
        with self.lock:
            return self.state

    def _process_segment(self, frames: list) -> Optional[str]:
        """Process a recorded segment: save to WAV, transcribe, return text."""
        if not frames:
            return None

        self.segment_counter += 1
        segment_filename = os.path.join(
            tempfile.gettempdir(),
            f"listen-seg-{self.session_timestamp}-{self.segment_counter:03d}.wav"
        )

        # Save frames to WAV
        wf = wave.open(segment_filename, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

        # Transcribe
        print("\r[transcribing]" + " " * 60, end="", flush=True)
        try:
            text = self.transcriber.transcribe(Path(segment_filename), self.language)
            # Strip whitespace to avoid double spaces when joining
            return text.strip()
        except Exception as e:
            print(f"\rTranscription error: {e}" + " " * 40)
            return None

    def _listen_for_keys(self) -> None:
        """Background thread: listen for keypresses to control recording state."""
        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                ch = sys.stdin.read(1)
                current = self._get_state()

                if ch == "\n" or ch == "\r":
                    if current == self.RECORDING:
                        self._set_state(self.PAUSED)
                    elif current == self.PAUSED:
                        self._set_state(self.RECORDING)
                elif ch == "q":
                    self._set_state(self.STOPPED)

                if self._get_state() == self.STOPPED:
                    break
        except Exception:
            self._set_state(self.STOPPED)

    def record(self) -> str:
        """Record audio with interactive pause/resume control. Returns transcribed text."""
        print("Interactive mode: recording started. Enter to pause/resume, q to stop\n")

        # Start keypress listener thread
        key_thread = threading.Thread(target=self._listen_for_keys, daemon=True)
        key_thread.start()

        # Open audio stream
        stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=None
        )

        current_segment_frames = []
        prev_state = self.RECORDING

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                current = self._get_state()

                # Detect state transitions
                if prev_state == self.RECORDING and current == self.PAUSED:
                    # Transition: RECORDING -> PAUSED, process the segment
                    text = self._process_segment(current_segment_frames)
                    if text:
                        self.text_segments.append(text)
                        # Clear the "transcribing" line and print the text on same line
                        print(f"\r> {text}" + " " * 20)
                    current_segment_frames = []

                if current == self.STOPPED:
                    # Stopped, process final segment if we were recording
                    if prev_state == self.RECORDING and current_segment_frames:
                        text = self._process_segment(current_segment_frames)
                        if text:
                            self.text_segments.append(text)
                            # Clear the "transcribing" line and print the text on same line
                            print(f"\r> {text}" + " " * 20)
                    else:
                        # Clear any remaining meter line
                        print("\r" + " " * 80, end="")
                    break

                int_data = array.array("h", data)
                amplitude = max(abs(x) for x in int_data)

                if current == self.RECORDING:
                    current_segment_frames.append(data)
                    is_silent = amplitude < SILENCE_THRESHOLD
                    print(f"\rAmplitude: {amplitude:5d}/{SILENCE_THRESHOLD} "
                          f"{'[silent]' if is_silent else '[SPEECH]'} [RECORDING]", end="")
                elif current == self.PAUSED:
                    # Read from stream to prevent buffer overflow, but discard
                    print(f"\rAmplitude: {amplitude:5d}/{SILENCE_THRESHOLD}             [PAUSED]  ", end="")

                prev_state = current

            except Exception as e:
                print(f"\rError reading audio: {e}")
                break

        print("\nDone recording.                                          ")

        stream.stop_stream()
        stream.close()

        return " ".join(self.text_segments)

    def cleanup(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_term_settings)
        self.p.terminate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


class Transcriber:
    def __init__(self, service="groq"):
        self.service = service
        if service == "groq":
            self.client = groq.Groq(api_key=os.getenv("GROQ_API_KEY_STT"))
        else:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY_STT"))

    def transcribe(self, audio_file: Path, language: Optional[str]) -> str:
        if self.service == "groq":
            response = self.client.audio.transcriptions.create(
                file=audio_file.open("rb"),
                model="whisper-large-v3",
                language=language
            )
        else:
            response = self.client.audio.transcriptions.create(
                file=audio_file.open("rb"),
                model="whisper-1",
                language=language
            )
        return response.text

# ____________________________________________________________________________________________

def transcribe_audio(audio_file_path: Path, language: str, service: str) -> str:
    """Transcribe audio file and return the text"""
    transcriber = Transcriber(service=service)
    text = transcriber.transcribe(audio_file_path, language)
    print(f"\nTranscribed text:\n{text}\n")
    return text


def copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard"""
    pyperclip.copy(text.strip())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    parser = argparse.ArgumentParser(description="Speech to Text Conversion")
    parser.add_argument("-l", "--language", type=str, default=None,
                      help="Optional language code (e.g., 'en', 'pl'). Auto-detected if not specified")
    parser.add_argument("-s", "--service", type=str, choices=['groq', 'whisper'],
                      default="groq", help="STT service to use")
    parser.add_argument("-i", "--input", type=str,
                      help="Process existing audio file instead of recording")
    args = parser.parse_args()

    # FILE MODE: Process existing audio file
    if args.input:
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: File '{args.input}' not found")
            return

        if input_path.suffix.lower() != ".wav":
            print(f"Warning: File '{args.input}' is not a .wav file, transcription may fail")

        print(f"File mode: processing {input_path.name}...")

        try:
            text = transcribe_audio(input_path, args.language, args.service)
            copy_to_clipboard(text)
        except Exception as e:
            print(f"Error processing file: {e}")

        return

    # INTERACTIVE RECORDING MODE (default)
    transcriber = Transcriber(service=args.service)
    with InteractiveRecorder(transcriber=transcriber, language=args.language) as recorder:
        text = recorder.record()

        if not text:
            return

        print(f"\nFull transcription:\n{text}\n")
        copy_to_clipboard(text)


if __name__ == "__main__":
    main()
