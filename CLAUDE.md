# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`letstalk` is a Python-based speech toolkit with two core utilities:
- **listen.py**: Speech-to-text (STT) using Whisper via Groq or OpenAI
- **talk.py**: Text-to-speech (TTS) using OpenAI's TTS models

Both scripts are designed as standalone command-line tools with no shared modules.

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
```

Required packages: pyaudio, openai, groq, pyperclip

## Environment Variables

The scripts require API keys configured as environment variables:
- `OPENAI_API_KEY_TTS`: For text-to-speech (talk.py)
- `OPENAI_API_KEY_STT`: For OpenAI Whisper transcription (listen.py)
- `GROQ_API_KEY_STT`: For Groq Whisper transcription (listen.py)

## Common Commands

### Text-to-Speech (talk.py)

Basic usage (reads from in.txt, outputs to out.mp3):
```bash
python talk.py
```

With options:
```bash
python talk.py -i input.txt -o output.mp3 -m tts-1-hd -v nova
```

Available voices: alloy, echo, fable, onyx, nova, shimmer
Available models: tts-1, tts-1-hd

### Speech-to-Text (listen.py)

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

## Architecture

### talk.py Architecture

- **Speaker class**: Handles OpenAI TTS API calls
  - Chunks text into MAX_CHARS (4096) segments at sentence boundaries
  - Processes chunks sequentially and concatenates audio
  - Smart chunking tries sentence breaks (. ! ?), then line breaks, then spaces

- **Main flow**: Read text → chunk if needed → generate audio → save as MP3

### listen.py Architecture

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

### Key Design Decisions

1. **Audio format**: Changed from float32 to int16 PCM for standard WAV compatibility
2. **Sampling rate**: 16kHz chosen as optimal for Whisper models
3. **Voice detection**: Amplitude-based (no ML) for simplicity and speed
4. **Text chunking**: Sentence-aware to avoid mid-word cuts in TTS
5. **Clipboard integration**: listen.py auto-copies transcription for quick pasting

### Important Constants

talk.py:
- `MAX_CHARS = 4096`: OpenAI TTS character limit per request

listen.py:
- `CHUNK = 1024`: Audio buffer size in frames
- `RATE = 16000`: Sample rate in Hz
- `SILENCE_THRESHOLD = 800`: Amplitude threshold for voice detection (range: -32768 to 32767)
- `SILENCE_DURATION = 2.0`: Seconds of silence before stopping recording
