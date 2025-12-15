# Vietnamese Anki Deck Generator

Generate Anki flashcard decks for learning Vietnamese, with AI-powered definitions, examples, and audio.

## Setup

1. Ensure you have Python 3.11 installed
2. Create and activate a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your Gemini API key (see [ENV_SETUP.md](ENV_SETUP.md))

## Usage

### 1. Generate Word List
Generate a list of the top 2000 most frequent Vietnamese words:
```bash
python 1_generate_list.py
```
Output: `raw_lemmas.csv`

### 2. Enrich with AI Data
Use Google Gemini to add definitions, parts of speech, and example sentences:
```bash
python 2_enrich_data.py
```
Output: `enriched_deck_data.csv`

**Note:** Requires `GEMINI_API_KEY` environment variable (see ENV_SETUP.md)

### 3. Synthesize Audio
Generate MP3 audio files for each word using Google Cloud Text-to-Speech:
```bash
python 3_synthesize_audio.py
```

Or specify voice preference:
```bash
python 3_synthesize_audio.py female  # vi-VN-Neural2-A (default)
python 3_synthesize_audio.py male    # vi-VN-Neural2-D
```

Output: 
- `audio/{rank}_{lemma}.mp3` files
- Updated `enriched_deck_data.csv` with `Audio_Path` column

**Note:** Requires Google Cloud credentials (see ENV_SETUP.md)

## Project Structure

- `1_generate_list.py` - Generate frequency-based Vietnamese word list
- `2_enrich_data.py` - Enrich words with AI-generated linguistic data
- `3_synthesize_audio.py` - Generate audio files for each word
- `raw_lemmas.csv` - Raw word list with frequency scores
- `enriched_deck_data.csv` - Words with definitions, examples, and audio paths
- `audio/` - Directory containing generated MP3 files
- `requirements.txt` - Python dependencies
- `ENV_SETUP.md` - API key and credentials setup instructions

## Dependencies

- **underthesea**: Vietnamese NLP toolkit
- **wordfreq**: Word frequency analysis
- **google-generativeai**: Google Gemini AI API
- **google-cloud-texttospeech**: Text-to-speech generation
- **genanki**: Anki deck generation
- **pandas**: Data manipulation
- **requests**: HTTP requests
- **python-dotenv**: Environment variable management

