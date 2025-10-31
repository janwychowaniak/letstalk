import argparse
import os

import openai

# ____________________________________________________________________________________________

MAX_CHARS = 4096  # OpenAI TTS character limit

class Speaker:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY_TTS'))
        
    def speak(self, text: str, model: str, voice: str) -> bytes:
        # Split text into chunks of MAX_CHARS, trying to break at sentences
        chunks = []
        while text:
            if len(text) <= MAX_CHARS:
                chunks.append(text)
                break
            
            # Find the last sentence break within the limit
            split_point = text[:MAX_CHARS].rfind('.')
            if split_point == -1:  # No sentence break found, try other delimiters
                split_point = text[:MAX_CHARS].rfind('!')
            if split_point == -1:
                split_point = text[:MAX_CHARS].rfind('?')
            if split_point == -1:  # Still no break found, try line break
                split_point = text[:MAX_CHARS].rfind('\n')
            if split_point == -1:  # Last resort: split at space
                split_point = text[:MAX_CHARS].rfind(' ')
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
        return b''.join(audio_chunks)

# ____________________________________________________________________________________________

def main():
    parser = argparse.ArgumentParser(description="Text to Speech Conversion")
    parser.add_argument("-i", "--input-file", type=str, default="in.txt",
                      help="Input text file (default: in.txt)")
    parser.add_argument("-o", "--output-file", type=str, default="out.mp3",
                      help="Output audio file (default: out.mp3)")
    parser.add_argument("-m", "--model", type=str, default="tts-1",
                      choices=["tts-1", "tts-1-hd"],
                      help="TTS model to use (default: tts-1)")
    parser.add_argument("-v", "--voice", type=str, default="alloy",
                      choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                      help="Voice to use (default: alloy)")
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            
        if not text:
            print(f"No text found in {args.input_file}")
            return
            
        print(f"input_len[/max_chars]: {len(text)}[/{MAX_CHARS}]")
        print(f"Converting text to speech using {args.model} with {args.voice} voice...")
        speaker = Speaker()
        audio_data = speaker.speak(text, args.model, args.voice)
        
        with open(args.output_file, 'wb') as f:
            f.write(audio_data)
            
        print(f"Audio saved to: {args.output_file}")
        
    except FileNotFoundError:
        print(f"Input file not found: {args.input_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
