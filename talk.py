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
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from datetime import datetime

import openai

# ____________________________________________________________________________________________

MAX_CHARS = 4096  # Conservative TTS request chunk size
OPENROUTER_TTS_URL = "https://openrouter.ai/api/v1/audio/speech"
OPENROUTER_TTS_MODEL = "google/gemini-3.1-flash-tts-preview"
OPENROUTER_TTS_VOICE = "Zephyr"
OPENROUTER_TTS_FORMAT = "pcm"
OPENROUTER_TTS_SAMPLE_RATE = 24000
OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "nova"
OPENAI_TTS_FORMAT = "mp3"
SENTENCE_ENDINGS = (".", "!", "?", ":", ";")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Speaker:
    def __init__(self, service: str):
        self.service = service
        if service == "openrouter":
            self.api_key = get_required_env("OPENROUTER_API_KEY_STT_TTS")
            self.model = OPENROUTER_TTS_MODEL
            self.voice = OPENROUTER_TTS_VOICE
            self.response_format = OPENROUTER_TTS_FORMAT
            self.output_suffix = "wav"
        elif service == "openai":
            self.client = openai.OpenAI(api_key=get_required_env("OPENAI_API_KEY_TTS"))
            self.model = OPENAI_TTS_MODEL
            self.voice = OPENAI_TTS_VOICE
            self.response_format = OPENAI_TTS_FORMAT
            self.output_suffix = "mp3"
        else:
            raise ValueError(f"Unsupported TTS service: {service}")

    def speak(self, text: str) -> bytes:
        # Split text into chunks of MAX_CHARS, trying to break at sentences
        chunks = []
        while text:
            if len(text) <= MAX_CHARS:
                chunks.append(text)
                break

            # Find the last sentence break within the limit
            split_point = text[:MAX_CHARS].rfind(".")
            if split_point == -1:  # No sentence break found, try other delimiters
                split_point = text[:MAX_CHARS].rfind("!")
            if split_point == -1:
                split_point = text[:MAX_CHARS].rfind("?")
            if split_point == -1:  # Still no break found, try line break
                split_point = text[:MAX_CHARS].rfind("\n")
            if split_point == -1:  # Last resort: split at space
                split_point = text[:MAX_CHARS].rfind(" ")
            if split_point == -1:  # No natural breaks, force split
                split_point = MAX_CHARS - 1

            print(f"chunk_len/remaining_len: {len(text[:split_point + 1])}/{len(text[split_point + 1:])}")

            chunks.append(text[:split_point + 1])
            text = text[split_point + 1:].lstrip()

        # Process each chunk
        audio_chunks = []
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            if total_chunks > 1:
                print(f"Processing chunk {i}/{total_chunks}...")
            audio_chunks.append(self._create_speech(chunk))

        # Combine all chunks into single audio stream
        return b"".join(audio_chunks)

    def _create_speech(self, text: str) -> bytes:
        if self.service == "openrouter":
            return self._create_openrouter_speech(text)

        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.response_format
        )
        if not response.content:
            raise RuntimeError("OpenAI returned an empty audio response")
        return response.content

    def _create_openrouter_speech(self, text: str) -> bytes:
        request_text = text.rstrip()
        if not request_text.endswith(SENTENCE_ENDINGS):
            # Gemini TTS can return a 200 with empty PCM for some unterminated phrases.
            request_text = f"{request_text}."

        payload = {
            "model": self.model,
            "input": request_text,
            "voice": self.voice,
            "response_format": self.response_format
        }
        request = urllib.request.Request(
            OPENROUTER_TTS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                content_type = response.headers.get("content-type", "")
                generation_id = response.headers.get("x-generation-id", "unknown")
                audio_data = response.read()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter speech failed ({e.code}): {error_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenRouter speech failed: {e.reason}") from e

        if not content_type.startswith("audio/"):
            preview = audio_data[:500].decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter returned non-audio response: {preview}")

        if not audio_data:
            raise RuntimeError(f"OpenRouter returned an empty audio response ({generation_id})")

        return audio_data

    def save_audio(self, audio_data: bytes, output_file: str) -> None:
        if not audio_data:
            raise RuntimeError("Refusing to save empty audio")

        if self.response_format == "pcm":
            with wave.open(output_file, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(OPENROUTER_TTS_SAMPLE_RATE)
                wf.writeframes(audio_data)
            return

        with open(output_file, "wb") as f:
            f.write(audio_data)

# ____________________________________________________________________________________________

def main():
    parser = argparse.ArgumentParser(
        description="Text to Speech Conversion",
        epilog="""
 Examples:
   # Read from input file
   %(prog)s -i story.txt
   
   # Direct text input
   %(prog)s -t "Hello world" -p
   
   # Piped stdin input
   echo "Hello world" | %(prog)s -p
   cat article.txt | %(prog)s -p
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Create mutually exclusive group for input source
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-i", "--input-file", type=str,
                      help="Input text file. Mutually exclusive with -t and piped stdin")
    input_group.add_argument("-t", "--text", type=str,
                      help="Text to convert (provide text directly in quotes). Mutually exclusive with -i and piped stdin")

    parser.add_argument("-p", "--play", action="store_true",
                      help="Play audio immediately using cvlc (after saving to temp file)")

    parser.add_argument("-s", "--service", type=str, default="openrouter",
                      choices=["openrouter", "openai"],
                      help="TTS service to use (default: openrouter)")
    args = parser.parse_args()

    # Detect piped stdin, but do not treat an empty non-tty stdin as an input source.
    stdin_text = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    stdin_has_data = bool(stdin_text)

    # Validate mutual exclusivity of input sources
    input_sources = sum([
        args.text is not None,
        args.input_file is not None,
        stdin_has_data
    ])

    if input_sources != 1:
        print("Error: Exactly one input source required: -t, -i, or piped stdin")
        return

    try:
        # Check cvlc availability if play mode requested
        if args.play:
            if not shutil.which("cvlc"):
                print("Error: cvlc not found. Please install VLC media player.")
                return

        # Determine text source (three mutually exclusive ways)
        if stdin_has_data:
            text = stdin_text
            source = "stdin"
        elif args.text:
            text = args.text.strip()
            source = "command line"
        else:
            # Use input file (default to in.txt if not specified)
            input_file = args.input_file if args.input_file else "in.txt"
            with open(input_file, "r", encoding="utf-8") as f:
                text = f.read().strip()
            source = input_file

        if not text:
            print(f"No text found from {source}")
            return

        speaker = Speaker(service=args.service)
        print(f"input_len[/max_chars]: {len(text)}[/{MAX_CHARS}]")
        print(f"Converting text to speech via {args.service} "
              f"using {speaker.model} with {speaker.voice} voice "
              f"as {speaker.response_format}...")
        audio_data = speaker.speak(text)

        # Determine output file (always temp with timestamp)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(
            tempfile.gettempdir(),
            f"talk-out-{timestamp}.{speaker.output_suffix}"
        )

        # Save audio file
        speaker.save_audio(audio_data, output_file)

        print(f"Audio saved to: {output_file}")

        # Play audio if requested
        if args.play:
            try:
                subprocess.run(["cvlc", "--rate=1.3", "--play-and-exit", output_file], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error playing audio: {e}")

        print(f"\nTo play:\nvlc --rate=1.3 --play-and-exit \"{output_file}\"")

    except FileNotFoundError:
        input_file = args.input_file if args.input_file else "in.txt"
        print(f"Input file not found: {input_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
