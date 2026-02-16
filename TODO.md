# TODO

## listen.py - Interactive Mode Punctuation and Capitalization Improvements

**Issue**: When using interactive recording mode (`-r`) with frequent pause/unpause cycles, Whisper transcription sometimes loses punctuation and capitalization quality. The audio recordings sound fine, but the abrupt transitions at pause boundaries may confuse the model, leading to:
- Missing or incorrect punctuation (periods, commas, question marks)
- Improper capitalization (mid-sentence capitals, missing sentence-start capitals)

**Potential solutions** (if punctuation quirks become annoying enough):

1. **Add silence padding at pause boundaries**
   - Insert brief silence (e.g., 100-200ms) between paused sections
   - Makes audio transitions smoother for Whisper
   - Requires generating silence frames in the correct format (int16 PCM, 16kHz mono)

2. **Post-process transcript with LLM**
   - Send raw Whisper output to GPT/Claude for punctuation correction
   - Prompt: "Fix punctuation and capitalization in this transcript, preserve all words"
   - Adds API call overhead but could significantly improve quality
   - Could be optional flag like `--fix-punctuation`

3. **Trim silence at pause boundaries**
   - Instead of naive concatenation, detect and trim trailing silence before pause
   - Trim leading silence after unpause
   - More complex than current approach but cleaner audio
   - Would need to adjust amplitude detection logic

**Current status**: Using segment-based transcription with immediate processing on pause. Per-segment audio files are preserved in `/tmp` for inspection if needed. Testing out this implementation in practice, in order to gather experience on how it works.

**Priority**: Low (only implement if punctuation/capitalization issues become frequent/annoying)
