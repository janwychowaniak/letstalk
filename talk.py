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
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

import openai

# ____________________________________________________________________________________________

MAX_CHARS = 4096  # OpenAI TTS character limit

class Speaker:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY_TTS"))

    def speak(self, text: str, model: str, voice: str) -> bytes:
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
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=chunk
            )
            audio_chunks.append(response.content)

        # Combine all chunks into single audio stream
        return b"".join(audio_chunks)

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

    parser.add_argument("-m", "--model", type=str, default="tts-1",
                      choices=["tts-1", "tts-1-hd"],
                      help="TTS model to use (default: tts-1)")
    parser.add_argument("-v", "--voice", type=str, default="nova",
                      choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                      help="Voice to use (default: nova)")
    args = parser.parse_args()

    # Detect if data is being piped via stdin
    stdin_has_data = not sys.stdin.isatty()

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
            text = sys.stdin.read().strip()
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

        print(f"input_len[/max_chars]: {len(text)}[/{MAX_CHARS}]")
        print(f"Converting text to speech using {args.model} with {args.voice} voice...")
        speaker = Speaker()
        audio_data = speaker.speak(text, args.model, args.voice)

        # Determine output file (always temp with timestamp)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(tempfile.gettempdir(), f"talk-out-{timestamp}.mp3")

        # Save audio file
        with open(output_file, "wb") as f:
            f.write(audio_data)

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
