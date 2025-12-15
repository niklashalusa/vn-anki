#!/usr/bin/env python3
"""
Test script to verify Google Cloud Text-to-Speech setup.

This script generates a test audio file to ensure your credentials are working
before running the full audio generation.
"""

import os
from pathlib import Path
from google.cloud import texttospeech
from dotenv import load_dotenv

load_dotenv()


def test_tts():
    """Test Text-to-Speech setup with a simple example."""
    
    # Check credentials
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not found in environment")
        print("\nPlease add it to your .env file:")
        print("  GOOGLE_APPLICATION_CREDENTIALS=/Users/niklas/Documents/GitHub/vn-anki/google-credentials.json")
        print("\nOr export it in your terminal:")
        print("  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/google-credentials.json'")
        print("\nSee ENV_SETUP.md for setup instructions.")
        return False
    
    if not os.path.exists(credentials_path):
        print(f"❌ Service account file not found: {credentials_path}")
        print(f"\nMake sure:")
        print(f"1. You've downloaded the JSON key from Google Cloud")
        print(f"2. You've saved it to the correct location")
        print(f"3. The path in .env is absolute (starts with /)")
        return False
    
    print(f"✓ Found credentials file: {os.path.basename(credentials_path)}")
    
    # Create test directory
    test_dir = Path("audio_test")
    test_dir.mkdir(exist_ok=True)
    
    try:
        print("\nConnecting to Google Cloud Text-to-Speech API...")
        client = texttospeech.TextToSpeechClient()
        
        # Test with both voices
        test_words = [
            ("xin chào", "vi-VN-Neural2-A", "female"),
            ("xin chào", "vi-VN-Neural2-D", "male")
        ]
        
        for text, voice_name, voice_type in test_words:
            print(f"\nTesting {voice_type} voice ({voice_name})...")
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="vi-VN",
                name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            output_file = test_dir / f"test_{voice_type}.mp3"
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            print(f"✓ Generated: {output_file}")
        
        print("\n" + "="*60)
        print("✅ SUCCESS! Your Google Cloud TTS setup is working!")
        print(f"✅ Test audio files saved to: {test_dir.absolute()}")
        print("="*60)
        print("\nYou can now run: python 3_synthesize_audio.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n" + "="*60)
        print("Common issues:")
        print("="*60)
        print("\n1. Text-to-Speech API not enabled in your project")
        print("   → Enable it: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com")
        print("\n2. Billing not enabled on your Google Cloud project")
        print("   → Required for Text-to-Speech API")
        print("   → Check: https://console.cloud.google.com/billing")
        print("\n3. Invalid or expired service account credentials")
        print("   → Re-download JSON key from:")
        print("   → https://console.cloud.google.com/iam-admin/serviceaccounts")
        print("\n4. Service account needs to be from the same project")
        print("   → where Text-to-Speech API is enabled")
        print("\nNote: No special IAM roles are required for the service account.")
        print("Just ensure the API is enabled and billing is active.")
        return False


if __name__ == "__main__":
    test_tts()

