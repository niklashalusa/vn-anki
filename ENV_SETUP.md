# Environment Setup

## 1. Gemini API Key (Required for Step 2)

To use the enrichment script (`2_enrich_data.py`), you need a Google Gemini API key.

### Steps:

1. **Get your API key:**
   - Visit: https://aistudio.google.com/app/apikey
   - Sign in with your Google account
   - Create a new API key

2. **Create a `.env` file** in the project root:
   ```bash
   touch .env
   ```

3. **Add your API key to `.env`:**
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

4. **Verify it's ignored by git:**
   The `.env` file is already in `.gitignore` so it won't be committed.

### Alternative: Use Environment Variable

Instead of a `.env` file, you can export the environment variable:

```bash
export GEMINI_API_KEY=your_actual_api_key_here
```

## 2. Google Cloud Text-to-Speech (Required for Step 3)

To use the audio synthesis script (`3_synthesize_audio.py`), you need Google Cloud credentials.

### Steps:

1. **Create a Google Cloud Project:**
   - Visit: https://console.cloud.google.com/
   - Create a new project or select an existing one

2. **Enable the Text-to-Speech API:**
   - Visit: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com
   - Click "Enable"

3. **Create a Service Account:**
   - Visit: https://console.cloud.google.com/iam-admin/serviceaccounts
   - Click "Create Service Account"
   - Name it (e.g., "anki-tts")
   - Grant role: "Cloud Text-to-Speech API User"
   - Click "Done"

4. **Create and Download JSON Key:**
   - Click on your new service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Save the file to your project directory (e.g., `google-credentials.json`)

5. **Add credentials path to `.env`:**
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
   ```
   
   Or use relative path:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
   ```

### Alternative: Use gcloud CLI

If you have gcloud CLI installed and authenticated:

```bash
gcloud auth application-default login
```

This creates default credentials that the script will use automatically.

### Test Your Setup:

After configuring credentials, test them with:

```bash
python test_audio.py
```

This will generate test audio files for both male and female voices.

### Important Security Notes:

- ⚠️ **NEVER commit your service account JSON file to git**
- The `.gitignore` already excludes `*.json` files
- Keep your credentials secure and private

### Voice Options:

- **vi-VN-Neural2-A**: Female voice, Northern accent (default)
- **vi-VN-Neural2-D**: Male voice, Northern accent

Both voices use Google's latest Neural2 technology for natural-sounding speech.

