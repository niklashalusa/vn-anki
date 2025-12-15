# Quick Start Guide

Complete guide to generate your Vietnamese Anki deck with audio.

## Prerequisites

- Python 3.11+ installed
- Google Gemini API key
- Google Cloud account with Text-to-Speech API enabled

## Step-by-Step Instructions

### 1. Setup Environment

```bash
# Navigate to project
cd /Users/niklas/Documents/GitHub/vn-anki

# Activate virtual environment (already created)
source .venv/bin/activate

# Verify packages are installed
pip list | grep -E "(wordfreq|underthesea|genanki|google)"
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env

# Add your keys (edit in your text editor)
# .env contents:
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

**Get your keys:**
- Gemini API: https://aistudio.google.com/app/apikey
- Google Cloud setup: See [ENV_SETUP.md](ENV_SETUP.md)

### 3. Test Google Cloud Setup (Optional but Recommended)

```bash
python test_audio.py
```

This generates test audio files to verify your credentials work.

### 4. Run the Pipeline

#### Step 1: Generate Word List
```bash
python 1_generate_list.py
```
- Output: `raw_lemmas.csv` (2000 words)
- Time: ~5 seconds

#### Step 2: Enrich with AI Data
```bash
python 2_enrich_data.py
```
- Output: `enriched_deck_data.csv`
- Time: ~3-4 minutes (100 API calls)
- Cost: Minimal (Gemini API is free tier friendly)

#### Step 3: Generate Audio Files
```bash
# Female voice (default)
python 3_synthesize_audio.py

# Or male voice
python 3_synthesize_audio.py male
```
- Output: `audio/{rank}_{lemma}.mp3` files + updated CSV
- Time: ~20-25 minutes (2000 files with 0.5s delay)
- Cost: Check Google Cloud pricing (first requests often free)

### 5. Verify Output

```bash
# Check CSV files
ls -lh *.csv

# Check audio files
ls -lh audio/ | head -20

# Count audio files
ls audio/*.mp3 | wc -l
```

You should have:
- `raw_lemmas.csv`: 2001 lines (header + 2000 words)
- `enriched_deck_data.csv`: 2001 lines with additional columns
- `audio/`: 2000 MP3 files

## Troubleshooting

### "GEMINI_API_KEY not found"
- Make sure `.env` file exists in project root
- Check the variable name is exactly `GEMINI_API_KEY`
- Try: `cat .env` to verify contents

### "GOOGLE_APPLICATION_CREDENTIALS not found"
- Make sure path in `.env` is absolute (starts with `/`)
- Verify JSON file exists: `ls -l /path/to/service-account.json`
- Alternative: Use `gcloud auth application-default login`

### "Permission Denied" errors
- Verify service account has "Cloud Text-to-Speech API User" role
- Check if Text-to-Speech API is enabled in your project
- Ensure billing is enabled (required for Google Cloud APIs)

### Rate Limit Errors
- Increase `rate_limit` parameter in scripts
- The default 0.5s should be safe for most cases

## Next Steps

After generating all files, you can:
1. Import into Anki (script coming next!)
2. Review the data in `enriched_deck_data.csv`
3. Customize voice, example sentences, or definitions
4. Generate additional decks with different word counts

## Cost Estimates

- **Gemini API**: Free tier (60 requests/minute)
- **Google Cloud TTS**: 
  - First 1 million characters/month: $4 per million
  - For 2000 words (~10,000 characters): < $0.05
  - Neural2 voices: Premium quality, slight premium pricing

## Support

- See [ENV_SETUP.md](ENV_SETUP.md) for detailed credential setup
- See [README.md](README.md) for project overview
- Check scripts for inline documentation

