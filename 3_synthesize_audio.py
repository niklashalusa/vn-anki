#!/usr/bin/env python3
"""
Generate audio files for Vietnamese words using Google Cloud Text-to-Speech.

This script reads enriched deck data and generates MP3 audio files for each word
using Vietnamese Neural2 voices with Northern accent.

Prerequisites:
- Google Cloud project with Text-to-Speech API enabled
- Service account with JSON key downloaded
- GOOGLE_APPLICATION_CREDENTIALS set in .env file
- Billing enabled on Google Cloud project

Voices Available:
- vi-VN-Neural2-A: Female, Northern accent (default)
- vi-VN-Neural2-D: Male, Northern accent

Usage:
    python 3_synthesize_audio.py          # Female voice
    python 3_synthesize_audio.py male     # Male voice
    python 3_synthesize_audio.py female   # Female voice

See ENV_SETUP.md for detailed setup instructions.
"""

import csv
import os
import time
from pathlib import Path
from google.cloud import texttospeech
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_tts_client():
    """
    Setup Google Cloud Text-to-Speech client.
    
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable pointing to
    service account JSON file.
    
    Setup Steps:
    1. Enable Text-to-Speech API in your Google Cloud project
    2. Create a service account (no special roles needed)
    3. Download JSON key and save to project directory
    4. Add path to .env file
    """
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError(
            "❌ GOOGLE_APPLICATION_CREDENTIALS not found in environment.\n\n"
            "Add it to your .env file:\n"
            "  GOOGLE_APPLICATION_CREDENTIALS=/Users/niklas/Documents/GitHub/vn-anki/google-credentials.json\n\n"
            "Or export it:\n"
            "  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/google-credentials.json'\n\n"
            "📋 Setup Instructions:\n"
            "1. Create/Select a Google Cloud Project:\n"
            "   https://console.cloud.google.com/\n\n"
            "2. Enable Text-to-Speech API:\n"
            "   https://console.cloud.google.com/apis/library/texttospeech.googleapis.com\n\n"
            "3. Create Service Account:\n"
            "   https://console.cloud.google.com/iam-admin/serviceaccounts\n"
            "   - Click 'Create Service Account'\n"
            "   - Name it (e.g., 'anki-tts')\n"
            "   - No special roles needed - just click 'Done'\n\n"
            "4. Create JSON Key:\n"
            "   - Click on your service account\n"
            "   - Go to 'Keys' tab\n"
            "   - 'Add Key' → 'Create new key' → JSON\n"
            "   - Save as 'google-credentials.json' in project folder\n\n"
            "5. Enable Billing (required for Text-to-Speech API)\n\n"
            "See ENV_SETUP.md for detailed instructions."
        )
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"❌ Service account file not found: {credentials_path}\n\n"
            "Please check:\n"
            "1. The file exists at the specified path\n"
            "2. The path in .env is absolute (starts with /)\n"
            "3. The filename matches exactly (check spelling)\n\n"
            "Current path from .env: {credentials_path}"
        )
    
    print(f"✓ Found credentials: {os.path.basename(credentials_path)}")
    
    try:
        client = texttospeech.TextToSpeechClient()
        print("✓ Successfully connected to Google Cloud Text-to-Speech API")
        return client
    except Exception as e:
        raise RuntimeError(
            f"❌ Failed to create Text-to-Speech client: {e}\n\n"
            "Common issues:\n"
            "1. Text-to-Speech API not enabled in your project\n"
            "2. Billing not enabled on your Google Cloud project\n"
            "3. Invalid or expired service account credentials\n\n"
            "Verify setup at: https://console.cloud.google.com/"
        )


def synthesize_audio(
    client: texttospeech.TextToSpeechClient,
    text: str,
    output_path: str,
    voice_name: str = "vi-VN-Neural2-A"
) -> bool:
    """
    Synthesize speech for the given text and save to file.
    
    Args:
        client: Text-to-speech client
        text: Text to synthesize
        output_path: Path to save the audio file
        voice_name: Voice to use (vi-VN-Neural2-A=Female, vi-VN-Neural2-D=Male)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Set the text input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code="vi-VN",
            name=voice_name
        )
        
        # Select the audio file type
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9  # Slightly slower for learning
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Write the response to the output file
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error synthesizing audio for '{text}': {e}")
        return False


def generate_audio_files(
    input_file: str = "enriched_deck_data.csv",
    output_file: str = "enriched_deck_data.csv",
    audio_dir: str = "audio",
    voice_name: str = "vi-VN-Neural2-A",
    rate_limit: float = 0.5
):
    """
    Generate audio files for all words in the enriched data.
    
    Args:
        input_file: Input CSV file path
        output_file: Output CSV file path (can be same as input)
        audio_dir: Directory to save audio files
        voice_name: Voice to use (vi-VN-Neural2-A=Female, vi-VN-Neural2-D=Male)
        rate_limit: Seconds to wait between API requests
    """
    # Setup
    print("Setting up Google Cloud Text-to-Speech client...")
    client = setup_tts_client()
    
    # Create audio directory
    audio_path = Path(audio_dir)
    audio_path.mkdir(exist_ok=True)
    print(f"Audio files will be saved to: {audio_path.absolute()}")
    
    # Read input data
    print(f"\nReading {input_file}...")
    words = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        words = list(reader)
    
    print(f"Loaded {len(words)} words")
    print(f"Using voice: {voice_name}")
    
    # Process each word
    success_count = 0
    fail_count = 0
    
    for i, word in enumerate(words, 1):
        rank = word['Rank']
        lemma = word['lemma']
        
        # Create filename
        # Sanitize lemma for filename (remove spaces and special chars)
        safe_lemma = lemma.replace(' ', '_').replace('/', '_')
        filename = f"{rank}_{safe_lemma}.mp3"
        output_path = audio_path / filename
        
        # Skip if file already exists
        if output_path.exists():
            print(f"[{i}/{len(words)}] Skipping {lemma} (file exists)")
            word['Audio_Path'] = f"[sound:{filename}]"
            success_count += 1
            continue
        
        # Generate audio
        print(f"[{i}/{len(words)}] Generating audio for: {lemma}")
        
        if synthesize_audio(client, lemma, str(output_path), voice_name):
            # Add Audio_Path in Anki format
            word['Audio_Path'] = f"[sound:{filename}]"
            success_count += 1
        else:
            word['Audio_Path'] = ""
            fail_count += 1
        
        # Rate limiting
        if i < len(words):
            time.sleep(rate_limit)
    
    # Write updated CSV
    print(f"\nWriting updated data to {output_file}...")
    
    # Get all fieldnames, add Audio_Path if not present
    fieldnames = list(words[0].keys())
    if 'Audio_Path' not in fieldnames:
        fieldnames.append('Audio_Path')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(words)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✓ Audio generation complete!")
    print(f"✓ Successfully generated: {success_count} files")
    if fail_count > 0:
        print(f"⚠️  Failed: {fail_count} files")
    print(f"✓ Updated CSV: {output_file}")
    print(f"✓ Audio directory: {audio_path.absolute()}")
    print(f"{'='*60}")
    
    # Show sample
    print(f"\nSample of first 3 words with audio:")
    for word in words[:3]:
        print(f"  {word['Rank']}. {word['lemma']}")
        print(f"     Audio: {word.get('Audio_Path', 'N/A')}")


def main():
    """Main entry point with voice selection."""
    import sys
    
    # Allow voice selection via command line
    voice = "vi-VN-Neural2-A"  # Default: Female
    
    if len(sys.argv) > 1:
        voice_arg = sys.argv[1].lower()
        if voice_arg in ['male', 'm', 'd']:
            voice = "vi-VN-Neural2-D"
            print("Selected: Male voice (vi-VN-Neural2-D)")
        elif voice_arg in ['female', 'f', 'a']:
            voice = "vi-VN-Neural2-A"
            print("Selected: Female voice (vi-VN-Neural2-A)")
        else:
            print(f"Unknown voice option: {voice_arg}")
            print("Using default: Female voice (vi-VN-Neural2-A)")
    else:
        print("Using default: Female voice (vi-VN-Neural2-A)")
        print("Tip: Pass 'male' or 'female' as argument to select voice")
    
    generate_audio_files(
        input_file="enriched_deck_data.csv",
        output_file="enriched_deck_data.csv",
        audio_dir="audio",
        voice_name=voice,
        rate_limit=0
    )


if __name__ == "__main__":
    main()

