# letstalk

When we are tired of typing and reading, let's make the computer capable of listening and speaking.

A simple Python toolkit for speech-to-text (STT) and text-to-speech (TTS) conversion.

## Features

- **Text-to-Speech (talk.py)**
  - Convert text to natural-sounding speech using OpenRouter or OpenAI
  - Input from file, command-line, or piped stdin
  - Save generated audio to `/tmp` or play immediately
  - OpenRouter Gemini TTS by default, OpenAI TTS optional
  - Automatic text chunking for long inputs

- **Speech-to-Text (listen.py)**
  - Interactive recording with manual pause/resume
  - Record from microphone or process existing audio files
  - Whisper transcription via Groq, OpenAI, or OpenRouter
  - Auto-copy transcription to clipboard
  - Audio files preserved in `/tmp` for quality inspection

## Installation

### Option 1: Using `uv` (Recommended)

If you have [uv](https://docs.astral.sh/uv/) installed, the scripts run directly with automatic dependency management:

```bash
./talk.py -t "Hello world" -p
./listen.py -s groq
```

### Option 2: Traditional Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run scripts with Python:
```bash
python talk.py -t "Hello world" -p
python listen.py -s groq
```

### API Keys Configuration

Set up API keys as environment variables:
```bash
export OPENAI_API_KEY_TTS="your-openai-api-key"
export OPENAI_API_KEY_STT="your-openai-api-key"
export GROQ_API_KEY_STT="your-groq-api-key"
export OPENROUTER_API_KEY_STT_TTS="your-openrouter-api-key"
```

### Optional: Install VLC for Playback

For immediate audio playback with `-p` flag:
```bash
# Ubuntu/Debian
sudo apt install vlc

# macOS
brew install --cask vlc
```

## Usage

Scripts can be run either with `uv` (if installed) or via `python`. All examples below show both options:

### Text-to-Speech (talk.py)

Quick command-line TTS with immediate playback:
```bash
./talk.py -t "Hello world" -p      # with uv
python talk.py -t "Hello world" -p # with pip
```

Convert file to audio:
```bash
./talk.py -i input.txt      # with uv
python talk.py -i input.txt # with pip
```

Use OpenAI instead of the default OpenRouter TTS:
```bash
./talk.py -s openai -t "Testing OpenAI TTS" -p      # with uv
python talk.py -s openai -t "Testing OpenAI TTS" -p # with pip
```

Pipe text via stdin:
```bash
echo "Hello world" | ./talk.py -p              # with uv
echo "Hello world" | python talk.py -p         # with pip
cat article.txt | ./talk.py -p
pbpaste | ./talk.py -p  # macOS clipboard
```

**Note:** Only one input method can be used at a time: `-i`, `-t`, or piped stdin.

**Options:**
- `-i/--input-file FILE`: Read text from file
- `-t/--text TEXT`: Provide text directly in quotes
- `-p/--play`: Play immediately with cvlc and save to temp file
- `-s/--service SERVICE`: TTS service (`openrouter` or `openai`, default: `openrouter`)

TTS models and voices are fixed by service:
- OpenRouter: `google/gemini-3.1-flash-tts-preview` with `Zephyr`, saved as WAV
- OpenAI: `tts-1` with `nova`, saved as MP3

### Speech-to-Text (listen.py)

**Recording** (starts immediately):
```bash
./listen.py -s groq      # with uv
python listen.py -s groq # with pip
```

Recording controls:
- Press **Enter** to pause/resume recording
- Press **q** to stop and finalize recording

Use OpenRouter STT:
```bash
./listen.py -s openrouter      # with uv
python listen.py -s openrouter # with pip
```

**Transcribe existing audio file:**
```bash
./listen.py -i recording.wav -s groq      # with uv
python listen.py -i recording.wav -s groq # with pip
```

**Options:**
- `-l/--language CODE`: Language code (e.g., 'en', 'pl'), auto-detected if not specified
- `-s/--service SERVICE`: STT service (`groq`, `openai`, or `openrouter`, default: `groq`)
- `-i/--input FILE`: Process existing audio file instead of recording

**Note:** All recorded audio segments are automatically saved to `/tmp/listen-seg-TIMESTAMP-NNN.wav` for later inspection if transcription quality needs verification.

## Examples

**Quick voice note with TTS playback:**
```bash
python talk.py -t "Remember to buy milk" -p
```

**Dictate a longer thought with pauses:**
```bash
python listen.py -s groq
# Press Enter to pause/resume, q to finish
```

**Transcribe existing meeting recording:**
```bash
python listen.py -i meeting.wav -l en -s groq
```

**Generate high-quality audiobook narration:**
```bash
python talk.py -i chapter1.txt -s openrouter
```

## License

MIT
