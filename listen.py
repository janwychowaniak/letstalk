import argparse
import os
from datetime import datetime
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
SILENCE_THRESHOLD = 800  # Need to adjust for int16 values (-32768 to 32767)
SILENCE_DURATION = 2.0  # Lower = more responsive to speech endings

# ____________________________________________________________________________________________

class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def record_until_silence(self, max_duration=None):
        stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=None
        )

        print("Listening... (speak to begin)")

        frames = []
        silent_chunks = 0
        has_speech = False
        total_chunks = 0
        max_chunks = float("inf") if max_duration is None else int(max_duration * RATE / CHUNK)

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                total_chunks += 1

                int_data = array.array("h", data)
                amplitude = max(abs(x) for x in int_data)
                is_silent = amplitude < SILENCE_THRESHOLD

                print(f"Amplitude: {amplitude:5d}/{SILENCE_THRESHOLD} {'[silent]' if is_silent else '[SPEECH]'}", end='\r')

                if is_silent:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                    has_speech = True

                # Stop if either:
                # 1. We've had enough silence after speech
                # 2. We've reached the maximum duration
                if (has_speech and silent_chunks > int(SILENCE_DURATION * RATE / CHUNK)) or \
                   total_chunks >= max_chunks:
                    break

            except Exception as e:
                print(f"Error reading audio: {e}")
                break

        print("Done recording.               ")

        stream.stop_stream()
        stream.close()

        return frames

    def save_frames(self, frames, filename):
        wf = wave.open(filename, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

    def cleanup(self):
        self.p.terminate()


class Transcriber:
    def __init__(self, service="groq"):
        self.service = service
        if service == "groq":
            self.client = groq.Groq(api_key=os.getenv("GROQ_API_KEY_STT"))
        else:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY_STT"))

    def transcribe(self, audio_file: Path, language: str) -> str:
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

def transcribe_and_copy(audio_file_path: Path, language: str, service: str) -> None:
    """Transcribe audio file and copy result to clipboard"""
    transcriber = Transcriber(service=service)
    text = transcriber.transcribe(audio_file_path, language)

    print(f"\nTranscribed text:\n{text}\n")
    pyperclip.copy(text.strip())


def main():
    parser = argparse.ArgumentParser(description="Speech to Text Conversion")
    parser.add_argument("-l", "--language", type=str, default="en",
                      help="Language code (e.g., 'en', 'pl')")
    parser.add_argument("-s", "--service", type=str, choices=['groq', 'whisper'],
                      default="groq", help="STT service to use")
    parser.add_argument("-d", "--duration", type=float, default=60,
                      help="Maximum recording duration in seconds (default: 60)")
    parser.add_argument("-b", "--backup", action="store_true",
                      help="Keep the audio file after processing (for debugging)")
    parser.add_argument("-i", "--input", type=str,
                      help="Process existing audio file instead of recording")
    args = parser.parse_args()

    # FILE MODE: Process existing audio file
    if args.input:
        input_path = Path(args.input)

        # Warn about ignored arguments
        ignored_args = []
        if args.duration != 60:  # Non-default duration
            ignored_args.append("--duration")
        if args.backup:
            ignored_args.append("--backup")

        if ignored_args:
            print(f"Note: {', '.join(ignored_args)} ignored in file mode")

        # Validate file existence
        if not input_path.exists():
            print(f"Error: File '{args.input}' not found")
            return

        # Basic WAV format check
        if input_path.suffix.lower() != ".wav":
            print(f"Warning: File '{args.input}' is not a .wav file, transcription may fail")

        print(f"File mode: processing {input_path.name}...")

        try:
            transcribe_and_copy(input_path, args.language, args.service)
        except Exception as e:
            print(f"Error processing file: {e}")

        return

    # RECORDING MODE: Record from microphone
    recorder = AudioRecorder()
    temp_audio_path = None

    try:
        frames = recorder.record_until_silence(max_duration=args.duration)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"listen-in-{timestamp}.wav")
        recorder.save_frames(frames, temp_audio_path)

        if args.backup:
            print(f"Debug mode: Audio saved to {temp_audio_path}")
        else:
            transcribe_and_copy(Path(temp_audio_path), args.language, args.service)

    finally:
        recorder.cleanup()
        if temp_audio_path and os.path.exists(temp_audio_path) and not args.backup:
            os.unlink(temp_audio_path)


if __name__ == "__main__":
    main()
