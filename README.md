# letstalk

When we are tired of typing and reading, let's make the computer capable of listening and speaking.

A simple Python toolkit for speech-to-text (STT) and text-to-speech (TTS) conversion.

## Features

- **Text-to-Speech (talk.py)**
  - Convert text to natural-sounding speech using OpenAI's TTS models
  - Input from file, command-line, or piped stdin
  - Save to MP3 or play immediately
  - Six voice options and two quality levels
  - Automatic text chunking for long inputs

- **Speech-to-Text (listen.py)**
  - Two recording modes: silence-based (automatic) or interactive (manual pause/resume)
  - Record from microphone or process existing audio files
  - Whisper transcription via Groq or OpenAI
  - Auto-copy transcription to clipboard
  - Audio files preserved in `/tmp` for quality inspection

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up API keys as environment variables:
```bash
export OPENAI_API_KEY_TTS="your-openai-api-key"
export OPENAI_API_KEY_STT="your-openai-api-key"
export GROQ_API_KEY_STT="your-groq-api-key"
```

3. (Optional) For immediate audio playback, install VLC:
```bash
# Ubuntu/Debian
sudo apt install vlc

# macOS
brew install --cask vlc
```

## Usage

### Text-to-Speech (talk.py)

Quick command-line TTS with immediate playback:
```bash
python talk.py -t "Hello world" -p
```

Convert file to audio:
```bash
python talk.py -i input.txt -o output.mp3
```

Use different voice and quality:
```bash
python talk.py -t "Testing nova voice" -v nova -m tts-1-hd -p
```

Default behavior (reads `in.txt`, saves `out.mp3`):
```bash
python talk.py
```

Pipe text via stdin:
```bash
echo "Hello world" | python talk.py -p
cat article.txt | python talk.py -o article.mp3
pbpaste | python talk.py -v nova -p  # macOS clipboard
```

**Note:** Only one input method can be used at a time: `-i`, `-t`, or piped stdin.

**Options:**
- `-i/--input-file FILE`: Read text from file (default: in.txt)
- `-t/--text TEXT`: Provide text directly in quotes
- `-o/--output-file FILE`: Save to specific file (default: out.mp3)
- `-p/--play`: Play immediately with cvlc and save to temp file
- `-m/--model MODEL`: TTS model (tts-1 or tts-1-hd, default: tts-1)
- `-v/--voice VOICE`: Voice selection (alloy, echo, fable, onyx, nova, shimmer, default: nova)

### Speech-to-Text (listen.py)

**Silence-based recording** (stops automatically after 2 seconds of silence):
```bash
python listen.py -s groq
```

**Interactive recording** (manual pause/resume control):
```bash
python listen.py -r -s groq
```

In interactive mode:
- Press **Enter** to start/pause/resume recording
- Press **q** to stop and finalize recording
- Great for longer dictation with thinking pauses

**Transcribe existing audio file:**
```bash
python listen.py -i recording.wav -s groq
```

**Options:**
- `-l/--language CODE`: Language code (e.g., 'en', 'pl'), auto-detected if not specified
- `-s/--service SERVICE`: STT service (groq or whisper, default: groq)
- `-d/--duration SECONDS`: Max recording duration in silence-based mode (default: 60)
- `-r/--record-interactive`: Interactive mode with manual pause/resume (mutually exclusive with -i)
- `-i/--input FILE`: Process existing audio file instead of recording (mutually exclusive with -r)

**Note:** All recorded audio files are automatically saved to `/tmp/listen-in-TIMESTAMP.wav` for later inspection if transcription quality needs verification.

## Examples

**Quick voice note with TTS playback:**
```bash
python talk.py -t "Remember to buy milk" -p
```

**Dictate a longer thought with pauses:**
```bash
python listen.py -r -s groq
# Press Enter to start, Enter to pause/resume, q to finish
```

**Quick voice transcription (automatic silence detection):**
```bash
python listen.py -s groq
# Speak, then wait 2 seconds - it stops automatically
```

**Transcribe existing meeting recording:**
```bash
python listen.py -i meeting.wav -l en -s groq
```

**Generate high-quality audiobook narration:**
```bash
python talk.py -i chapter1.txt -o chapter1.mp3 -m tts-1-hd -v nova
```

## License

MIT
