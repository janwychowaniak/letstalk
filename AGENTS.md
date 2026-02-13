# DEVELOPMENT.md

This file provides comprehensive guidance for understanding, using, and developing within the `letstalk` repository. It is intended for both human developers and AI assistants.

## 1. Project Overview

`letstalk` is a Python-based speech toolkit with two core utilities:
- **listen.py**: Speech-to-text (STT) using Whisper via Groq or OpenAI
- **talk.py**: Text-to-speech (TTS) using OpenAI's TTS models

Both scripts are designed as standalone command-line tools with no shared modules.

## 2. Setup and Usage

### 2.1. Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
```

Required packages: pyaudio, openai, groq, pyperclip

### 2.2. Environment Variables

The scripts require API keys configured as environment variables:
- `OPENAI_API_KEY_TTS`: For text-to-speech (talk.py)
- `OPENAI_API_KEY_STT`: For OpenAI Whisper transcription (listen.py)
- `GROQ_API_KEY_STT`: For Groq Whisper transcription (listen.py)

### 2.3. Common Commands

#### Text-to-Speech (talk.py)

Basic usage (reads from in.txt, outputs to out.mp3):
```bash
python talk.py
```

Command-line text input with immediate playback (requires cvlc):
```bash
python talk.py -t "Hello world" -p
```

File-based input with custom output:
```bash
python talk.py -i input.txt -o output.mp3 -m tts-1-hd -v nova
```

Pipe text via stdin:
```bash
echo "Hello world" | python talk.py -p
cat article.txt | python talk.py -o article.mp3
```

Options:
- `-i/--input-file`: Read text from file (mutually exclusive with -t and piped stdin)
- `-t/--text`: Provide text directly in quotes (mutually exclusive with -i and piped stdin)
- `-o/--output-file`: Save to specific file (mutually exclusive with -p)
- `-p/--play`: Play immediately with cvlc and save to temp file (mutually exclusive with -o)
- `-m/--model`: TTS model (tts-1 or tts-1-hd)
- `-v/--voice`: Voice selection (alloy, echo, fable, onyx, nova, shimmer)

Available voices: alloy, echo, fable, onyx, nova, shimmer
Available models: tts-1, tts-1-hd

#### Speech-to-Text (listen.py)

Record from microphone:
```bash
python listen.py -l en -s groq
```

Process existing audio file:
```bash
python listen.py -i recording.wav -l en -s groq
```

Options:
- `-l/--language`: Language code (e.g., 'en', 'pl')
- `-s/--service`: STT service (groq or whisper)
- `-d/--duration`: Max recording duration in seconds (default: 60)
- `-b/--backup`: Keep audio file after processing
- `-i/--input`: Process existing audio file instead of recording

## 3. Architecture and Design

### 3.1. talk.py Architecture

- **Speaker class**: Handles OpenAI TTS API calls
  - Chunks text into MAX_CHARS (4096) segments at sentence boundaries
  - Processes chunks sequentially and concatenates audio
  - Smart chunking tries sentence breaks (. ! ?), then line breaks, then spaces

- **Input modes** (mutually exclusive):
  - File mode: Read from file specified with -i (default: in.txt)
  - Direct mode: Accept text from command-line with -t
  - Stdin mode: Read from piped stdin (implicit detection via sys.stdin.isatty())

- **Output modes** (mutually exclusive):
  - Save mode: Write to file specified with -o (default: out.mp3)
  - Play mode: Save to timestamped temp file and play with cvlc

- **Main flow**: Read/receive text → chunk if needed → generate audio → save MP3 → optionally play

### 3.2. listen.py Architecture

- **AudioRecorder class**: Manages PyAudio recording
  - Records in mono, 16kHz, 16-bit PCM format
  - Uses amplitude-based voice activity detection
  - Stops after SILENCE_DURATION seconds of silence (2.0s)
  - Configurable SILENCE_THRESHOLD (800) and max duration

- **Transcriber class**: Supports two STT services
  - Groq: whisper-large-v3 model
  - OpenAI: whisper-1 model
  - Same interface for both services

- **Two modes**:
  - Recording mode: Record → save temp WAV → transcribe → copy to clipboard → cleanup
  - File mode: Read existing WAV → transcribe → copy to clipboard

### 3.3. Key Design Decisions

1. **Audio format**: Changed from float32 to int16 PCM for standard WAV compatibility
2. **Sampling rate**: 16kHz chosen as optimal for Whisper models
3. **Voice detection**: Amplitude-based (no ML) for simplicity and speed
4. **Text chunking**: Sentence-aware to avoid mid-word cuts in TTS
5. **Clipboard integration**: listen.py auto-copies transcription for quick pasting
6. **Mutual exclusivity**: Both input modes (-i/-t) and output modes (-o/-p) in talk.py are enforced at argparse level
7. **Stdin input detection**: talk.py uses sys.stdin.isatty() to detect piped input, with manual validation for mutual exclusivity since argparse doesn't support stdin in mutually exclusive groups
8. **Temp file preservation**: Play mode keeps generated audio in temp directory for later replay
9. **cvlc integration**: Immediate playback mode checks for cvlc availability before processing

### 3.4. Important Constants

**talk.py:**
- `MAX_CHARS = 4096`: OpenAI TTS character limit per request

**listen.py:**
- `CHUNK = 1024`: Audio buffer size in frames
- `RATE = 16000`: Sample rate in Hz
- `SILENCE_THRESHOLD = 800`: Amplitude threshold for voice detection (range: -32768 to 32767)
- `SILENCE_DURATION = 2.0`: Seconds of silence before stopping recording

## 4. Development Guidelines

### 4.1. Testing & Linting

#### Testing
This project currently has no automated test suite. When testing:
- Manually test both scripts with various input combinations
- Test edge cases: empty input, very long text, missing files, invalid API keys
- Verify mutually exclusive argument groups work correctly
- Test both input modes and both output modes for talk.py
- Test both recording and file modes for listen.py

#### Linting
No formal linter configuration exists. Follow the code style guidelines below.

### 4.2. Code Style Guidelines

#### Import Organization
Organize imports in three groups, separated by blank lines:
1. Standard library imports (alphabetical, multi-line imports use `from X import Y`)
2. Third-party imports (alphabetical, one per line)
3. Local imports (this project has none)

Example:
```python
import argparse
import os
from datetime import datetime

import openai
import pyaudio
```

#### Formatting
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Soft limit ~100 chars, hard limit ~120 chars
- **Blank lines**: Two blank lines before top-level classes and functions
- **Section separators**: Use comment line with underscores for visual separation:
  ```python
  # ____________________________________________________________________________________________
  ```
- **String quotes**: Double quotes for strings
- **f-strings**: Preferred for string formatting

#### Type Hints
- Use type hints for function signatures (parameters and return types)
- Examples: `def speak(self, text: str, model: str, voice: str) -> bytes:`
- Use `Path` for file paths, `str` for text, `bytes` for binary data
- No need for type hints on simple variables or `__init__` methods without complex logic

#### Naming Conventions
- **Classes**: PascalCase (e.g., `AudioRecorder`, `Speaker`)
- **Functions/methods**: snake_case (e.g., `record_until_silence`, `save_frames`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_CHARS`, `SILENCE_THRESHOLD`)
- **Variables**: snake_case (e.g., `audio_data`, `temp_file`)
- **Private methods**: Prefix with underscore if truly internal (rare in this codebase)

#### Comments and Documentation
- Use clear, concise comments explaining WHY, not WHAT
- Document non-obvious behavior (e.g., chunking strategy, silence detection)
- Inline comments should be brief and focused
- Add comments for important constants explaining their purpose and units
- Example: `SILENCE_DURATION = 2.0  # Seconds of silence before stopping recording`

#### Error Handling
- Use try-except blocks for file I/O, API calls, and external process execution
- Print user-friendly error messages (not raw exceptions for expected errors)
- Always cleanup resources (PyAudio, temp files) in finally blocks
- Use `shutil.which()` to check for external dependencies before use
- Examples:
  ```python
  try:
      with open(input_file, "r") as f:
          text = f.read()
  except FileNotFoundError:
      print(f"Input file not found: {input_file}")
      return
  ```

#### Argument Parsing
- Use `argparse` with clear help messages
- Use `add_mutually_exclusive_group()` for conflicting options
- Provide sensible defaults
- Validate inputs early (e.g., check file existence, API key presence)

#### Class & Function Design
- Keep classes and functions simple and focused (single responsibility)
- Use `__init__` for setup, not complex logic
- Use early returns for error conditions
- Avoid deep nesting (max 3 levels)

#### File Operations
- Use `Path` from pathlib for file path manipulation
- Use context managers (`with` statements) for file I/O
- Use `tempfile` module for temporary files

#### API Interactions
- Store API keys in environment variables (never hardcode)
- Use descriptive environment variable names (e.g., `OPENAI_API_KEY_TTS`)
- Initialize API clients in `__init__` methods
- Handle API errors gracefully with try-except

### 4.3. Common Implementation Patterns

- **Chunking Long Text**: See `Speaker.speak()` for sentence-aware chunking that tries delimiters in order: `.`, `!`, `?`, `
`, space.

- **Voice Activity Detection**: See `AudioRecorder.record_until_silence()` for amplitude-based silence detection using a rolling silence counter.

- **Mutually Exclusive Modes**: Use argparse groups to enforce exclusive options (e.g., `-i` vs `-t`, `-o` vs `-p`).

- **Stdin Input Detection**: See `main()` in `talk.py` for implicit stdin pipe detection using `sys.stdin.isatty()`. Manual validation ensures mutual exclusivity with `-i` and `-t` flags.

### 4.4. Architecture Constraints

- **No shared modules**: Each script must be fully standalone
- **No complex dependencies**: Avoid adding heavy ML libraries
- **CLI-first**: These are command-line tools, not libraries
- **Minimal state**: Prefer stateless functions where possible
