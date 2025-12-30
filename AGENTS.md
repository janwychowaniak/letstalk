# AGENTS.md

This file provides coding guidelines for AI agents working in the `letstalk` repository.

## Project Overview

`letstalk` is a minimalist Python speech toolkit with two standalone CLI utilities:
- **talk.py**: Text-to-speech using OpenAI TTS
- **listen.py**: Speech-to-text using Whisper (Groq or OpenAI)

Both scripts are completely independent with no shared modules.

## Build/Lint/Test Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the scripts
```bash
# Text-to-speech
python talk.py -t "Hello world" -p

# Speech-to-text
python listen.py -l en -s groq
```

### Testing
This project currently has no automated test suite. When testing:
- Manually test both scripts with various input combinations
- Test edge cases: empty input, very long text, missing files, invalid API keys
- Verify mutually exclusive argument groups work correctly
- Test both input modes and both output modes for talk.py
- Test both recording and file modes for listen.py

### Linting
No formal linter configuration exists. Follow the code style guidelines below.

## Code Style Guidelines

### Import Organization
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

### Formatting
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Soft limit ~100 chars, hard limit ~120 chars
- **Blank lines**: Two blank lines before top-level classes and functions
- **Section separators**: Use comment line with underscores for visual separation:
  ```python
  # ____________________________________________________________________________________________
  ```
- **String quotes**: Double quotes for strings
- **f-strings**: Preferred for string formatting

### Type Hints
- Use type hints for function signatures (parameters and return types)
- Examples: `def speak(self, text: str, model: str, voice: str) -> bytes:`
- Use `Path` for file paths, `str` for text, `bytes` for binary data
- No need for type hints on simple variables or `__init__` methods without complex logic

### Naming Conventions
- **Classes**: PascalCase (e.g., `AudioRecorder`, `Speaker`)
- **Functions/methods**: snake_case (e.g., `record_until_silence`, `save_frames`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_CHARS`, `SILENCE_THRESHOLD`)
- **Variables**: snake_case (e.g., `audio_data`, `temp_file`)
- **Private methods**: Prefix with underscore if truly internal (rare in this codebase)

### Comments and Documentation
- Use clear, concise comments explaining WHY, not WHAT
- Document non-obvious behavior (e.g., chunking strategy, silence detection)
- Inline comments should be brief and focused
- Add comments for important constants explaining their purpose and units
- Example: `SILENCE_DURATION = 2.0  # Seconds of silence before stopping recording`

### Error Handling
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

### Argument Parsing
- Use `argparse` with clear help messages
- Use `add_mutually_exclusive_group()` for conflicting options
- Provide sensible defaults
- Validate inputs early (e.g., check file existence, API key presence)

### Class Design
- Keep classes simple and focused (single responsibility)
- Use `__init__` for setup, not complex logic
- Prefer instance methods over static methods
- Use composition over inheritance (this project uses no inheritance)
- Always provide cleanup methods (`cleanup()`, resource management)

### Function Design
- Keep functions focused and relatively short (<60 lines)
- Use early returns for error conditions
- Avoid deep nesting (max 3 levels)
- Extract complex logic into helper functions
- Return meaningful values (bytes, str, Path) not generic types

### Constants and Configuration
- Define all configuration constants at module top
- Use UPPER_SNAKE_CASE with descriptive names
- Add inline comments explaining units and ranges
- Group related constants together

### File Operations
- Use `Path` from pathlib for file path manipulation
- Use context managers (`with` statements) for file I/O
- Always specify encoding for text files (`encoding="utf-8"`)
- Use `tempfile` module for temporary files
- Clean up temp files unless debug/backup flag is set

### API Interactions
- Store API keys in environment variables (never hardcode)
- Use descriptive environment variable names (e.g., `OPENAI_API_KEY_TTS`)
- Initialize API clients in `__init__` methods
- Handle API errors gracefully with try-except

### Audio Processing
- Use standard formats: 16-bit PCM, 16kHz, mono for Whisper compatibility
- Use `pyaudio.paInt16` for format (not float32)
- Use `array.array` for efficient amplitude calculations
- Close streams properly in finally blocks

### User Feedback
- Print progress messages for long operations (e.g., "Processing chunk 2/5...")
- Use carriage return (`\r`) for real-time updates (e.g., amplitude display)
- Show clear completion messages with file paths
- Provide replay commands when saving temp files

### Testing Considerations
When modifying code, manually verify:
- All argument combinations work correctly
- Mutually exclusive groups are enforced
- Error messages are user-friendly
- Resources are properly cleaned up
- API calls succeed with valid keys
- File paths are handled correctly on different platforms

## Common Patterns

### Chunking Long Text
See `Speaker.speak()` for sentence-aware chunking that tries delimiters in order: `.`, `!`, `?`, `\n`, space.

### Voice Activity Detection
See `AudioRecorder.record_until_silence()` for amplitude-based silence detection using rolling silence counter.

### Mutually Exclusive Modes
Use argparse groups to enforce exclusive options (e.g., `-i` vs `-t`, `-o` vs `-p`).

## Architecture Constraints

- **No shared modules**: Each script must be fully standalone
- **No complex dependencies**: Avoid adding heavy ML libraries
- **CLI-first**: These are command-line tools, not libraries
- **Minimal state**: Prefer stateless functions where possible
