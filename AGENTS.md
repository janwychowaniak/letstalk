# DEVELOPMENT.md

This file provides comprehensive guidance for understanding, using, and developing within the `letstalk` repository. It is intended for both human developers and AI assistants.

## 1. Project Overview

`letstalk` is a Python-based speech toolkit with two core utilities:
- **listen.py**: Speech-to-text (STT) using Whisper via Groq or OpenAI
- **talk.py**: Text-to-speech (TTS) using OpenAI's TTS models

Both scripts are designed as standalone command-line tools with no shared modules.

## 2. Setup and Usage

### 2.1. Dependencies

Scripts now support **uv** for automatic dependency management via Python script metadata (PEP 723). Both installation methods work:

**Option 1: Using `uv` (Recommended)**
```bash
./talk.py -t "Hello world" -p
./listen.py -s groq
```
Dependencies are automatically managed via the script metadata block.

**Option 2: Traditional pip**
```bash
pip install -r requirements.txt
python talk.py -t "Hello world" -p
python listen.py -s groq
```

Required packages: pyaudio, openai, groq, pyperclip

### 2.2. Environment Variables

The scripts require API keys configured as environment variables:
- `OPENAI_API_KEY_TTS`: For text-to-speech (talk.py)
- `OPENAI_API_KEY_STT`: For OpenAI Whisper transcription (listen.py)
- `GROQ_API_KEY_STT`: For Groq Whisper transcription (listen.py)

### 2.3. Common Commands

#### Text-to-Speech (talk.py)

Command-line text input with immediate playback (requires cvlc):
```bash
./talk.py -t "Hello world" -p      # with uv
python talk.py -t "Hello world" -p # with pip
```

File-based input with playback:
```bash
./talk.py -i input.txt -p      # with uv
python talk.py -i input.txt -p # with pip
```

Pipe text via stdin with playback:
```bash
echo "Hello world" | ./talk.py -p      # with uv
echo "Hello world" | python talk.py -p # with pip
cat article.txt | ./talk.py -p
```

Without -p, audio is saved to temp file and playback command is printed.

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

**Silence-based recording** (default):
```bash
./listen.py -s groq      # with uv
python listen.py -s groq # with pip
```

**Interactive recording** with manual pause/resume:
```bash
./listen.py -r -s groq      # with uv
python listen.py -r -s groq # with pip
```

**Process existing audio file**:
```bash
./listen.py -i recording.wav -s groq      # with uv
python listen.py -i recording.wav -s groq # with pip
```

Options:
- `-l/--language`: Language code (e.g., 'en', 'pl')
- `-s/--service`: STT service (groq or whisper)
- `-d/--duration`: Max recording duration in seconds (default: 60, ignored in interactive mode)
- `-r/--record-interactive`: Interactive recording mode with manual pause/resume controls (mutually exclusive with -i)
- `-i/--input`: Process existing audio file instead of recording (mutually exclusive with -r)

**Interactive mode controls:**
- Press **Enter** to start recording (from READY state)
- Press **Enter** to pause/unpause recording (toggles between RECORDING and PAUSED)
- Press **q** to stop and finalize recording (from any state)

**Interactive mode behavior:**
- Each pause triggers immediate transcription of the recorded segment
- Transcribed text appears incrementally on screen (prefixed with '> ')
- Final transcription (all segments joined) is copied to clipboard when recording stops
- Per-segment audio files are preserved in `/tmp` as listen-seg-YYYYMMDD-HHMMSS-NNN.wav

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

- **AudioRecorder class**: Silence-based recording (default mode)
  - Records in mono, 16kHz, 16-bit PCM format
  - Uses amplitude-based voice activity detection
  - Stops after SILENCE_DURATION seconds of silence (2.0s)
  - Configurable SILENCE_THRESHOLD (800) and max duration
  - Context manager: automatic PyAudio cleanup

- **InteractiveRecorder class**: Manual pause/resume recording with incremental transcription
  - Same audio format as AudioRecorder (mono, 16kHz, int16 PCM)
  - State machine: READY → RECORDING ↔ PAUSED → STOPPED
  - Background daemon thread listens for keypresses using tty/termios cbreak mode
  - Thread-safe state management via threading.Lock
  - Audio stream stays open during pauses (reads but discards frames to prevent buffer overflow)
  - **Incremental transcription**: Each pause triggers immediate STT transcription of the segment
    - Segments transcribed independently as they're recorded (not concatenated)
    - Per-segment WAV files saved as listen-seg-YYYYMMDD-HHMMSS-NNN.wav in /tmp
    - Transcribed text displayed incrementally on screen (prefixed with '> ')
    - Final transcription (joined segments) copied to clipboard when recording stops
    - Synchronous transcription with '[transcribing]' indicator during processing
  - Shows amplitude meter + state indicator: [RECORDING] / [PAUSED]
  - Context manager: restores terminal settings and cleans up PyAudio

- **Transcriber class**: Supports two STT services
  - Groq: whisper-large-v3 model
  - OpenAI: whisper-1 model
  - Same interface for both services

- **Three modes**:
  - Silence-based recording mode: Record → save temp WAV → transcribe → copy to clipboard (audio file preserved)
  - Interactive recording mode: Record with manual pause/resume → transcribe each segment incrementally → join and copy full text to clipboard (segment audio files preserved)
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
10. **Audio file persistence**: listen.py always preserves recorded audio files in /tmp for debugging transcription quality
11. **Interactive recording**: Uses tty/termios for non-blocking keypress detection with background thread, state machine ensures clean transitions
12. **Incremental transcription**: Interactive mode transcribes each segment immediately on pause, providing real-time feedback and reducing post-recording editing needs

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

- **Incremental Transcription**: See `InteractiveRecorder._process_segment()` and `InteractiveRecorder.record()` in `listen.py` for segment-based recording with immediate transcription on state transitions (RECORDING → PAUSED, RECORDING → STOPPED).

### 4.4. Architecture Constraints

- **No shared modules**: Each script must be fully standalone
- **No complex dependencies**: Avoid adding heavy ML libraries
- **CLI-first**: These are command-line tools, not libraries
- **Minimal state**: Prefer stateless functions where possible
