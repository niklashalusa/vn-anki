#!/usr/bin/env python3
"""
Create Anki deck package (.apkg) from enriched Vietnamese word data.

This script reads the enriched CSV data and audio files, then generates
a complete Anki deck package ready for import.

Output: Vietnamese_Core_2000.apkg
"""

import csv
import os
from pathlib import Path
import genanki
import random


# Define custom Anki Note Model
VIETNAMESE_MODEL = genanki.Model(
    1607392319,  # Unique model ID (random, but consistent)
    'Vietnamese Core Vocabulary',
    fields=[
        {'name': 'Lemma'},
        {'name': 'Definition'},
        {'name': 'Audio'},
        {'name': 'Sentence_VI'},
        {'name': 'Sentence_EN'},
        {'name': 'POS'},
    ],
    templates=[
        {
            'name': 'Vietnamese → English',
            'qfmt': '''
                <div class="card">
                    <div class="lemma">{{Lemma}}</div>
                    <div class="audio">{{Audio}}</div>
                    <div class="pos">{{POS}}</div>
                </div>
            ''',
            'afmt': '''
                <div class="card">
                    <div class="lemma">{{Lemma}}</div>
                    <div class="audio">{{Audio}}</div>
                    <div class="pos">{{POS}}</div>
                    <hr id="answer">
                    <div class="definition">{{Definition}}</div>
                    <div class="example">
                        <div class="example-vi">{{Sentence_VI}}</div>
                        <div class="example-en">{{Sentence_EN}}</div>
                    </div>
                </div>
            ''',
        },
    ],
    css='''
        .card {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 20px;
            text-align: center;
            color: #333;
            background-color: #fff;
            padding: 20px;
        }
        
        .lemma {
            font-size: 48px;
            font-weight: bold;
            color: #2196F3;
            margin: 20px 0;
            line-height: 1.2;
        }
        
        .audio {
            margin: 15px 0;
        }
        
        .pos {
            font-size: 16px;
            color: #666;
            font-style: italic;
            text-transform: lowercase;
            margin: 10px 0;
        }
        
        .definition {
            font-size: 24px;
            font-weight: 500;
            color: #4CAF50;
            margin: 20px 0;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 8px;
        }
        
        .example {
            margin: 25px 0;
            padding: 15px;
            background-color: #fff3e0;
            border-radius: 8px;
            border-left: 4px solid #FF9800;
        }
        
        .example-vi {
            font-size: 22px;
            color: #333;
            margin: 10px 0;
            font-weight: 500;
        }
        
        .example-en {
            font-size: 18px;
            color: #666;
            margin: 10px 0;
            font-style: italic;
        }
        
        hr {
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 20px 0;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 600px) {
            .lemma {
                font-size: 36px;
            }
            .definition {
                font-size: 20px;
            }
            .example-vi {
                font-size: 18px;
            }
        }
    ''',
)


def create_anki_deck(
    input_file: str = "enriched_deck_data.csv",
    audio_dir: str = "audio",
    output_file: str = "Vietnamese_Core_2000.apkg",
    deck_name: str = "Vietnamese Core 2000",
    deck_description: str = "Top 2000 most frequent Vietnamese words with audio, definitions, and examples"
):
    """
    Create Anki deck package from enriched data.
    
    Args:
        input_file: Path to enriched CSV data
        audio_dir: Directory containing audio files
        output_file: Output .apkg filename
        deck_name: Name of the deck in Anki
        deck_description: Description shown in Anki
    """
    print("="*60)
    print("Creating Anki Deck Package")
    print("="*60)
    
    # Check input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"❌ Input file not found: {input_file}\n"
            f"Please run 2_enrich_data.py first to create the enriched data."
        )
    
    # Create deck with unique ID
    deck_id = random.randrange(1 << 30, 1 << 31)
    deck = genanki.Deck(deck_id, deck_name)
    deck.description = deck_description
    
    # Read CSV data
    print(f"\n📖 Reading data from {input_file}...")
    words = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        words = list(reader)
    
    print(f"✓ Loaded {len(words)} words")
    
    # Collect media files
    media_files = []
    audio_path = Path(audio_dir)
    
    # Create notes
    print(f"\n📝 Creating Anki notes...")
    notes_created = 0
    notes_failed = 0
    
    for i, word in enumerate(words, 1):
        try:
            rank = word.get('Rank', '')
            lemma = word.get('lemma', '')
            definition = word.get('english_definition', '')
            pos = word.get('pos', '')
            sentence_vi = word.get('example_vi', '')
            sentence_en = word.get('example_en', '')
            audio_path_str = word.get('Audio_Path', '')
            
            # Skip if essential data is missing
            if not lemma or not definition:
                print(f"⚠️  Skipping word {rank}: Missing essential data")
                notes_failed += 1
                continue
            
            # Extract audio filename from Anki format [sound:filename.mp3]
            audio_filename = ""
            if audio_path_str:
                # Extract filename from [sound:filename.mp3]
                if audio_path_str.startswith('[sound:') and audio_path_str.endswith(']'):
                    audio_filename = audio_path_str[7:-1]  # Remove [sound: and ]
                    
                    # Check if audio file exists
                    full_audio_path = audio_path / audio_filename
                    if full_audio_path.exists() and str(full_audio_path) not in media_files:
                        media_files.append(str(full_audio_path))
            
            # Create note
            note = genanki.Note(
                model=VIETNAMESE_MODEL,
                fields=[
                    lemma,
                    definition,
                    audio_path_str,  # Keep in [sound:filename] format for Anki
                    sentence_vi,
                    sentence_en,
                    pos,
                ],
                tags=['vietnamese', 'core-vocabulary', f'rank-{rank}']
            )
            
            deck.add_note(note)
            notes_created += 1
            
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(words)} words processed...")
            
        except Exception as e:
            print(f"❌ Error creating note for word {i}: {e}")
            notes_failed += 1
    
    print(f"\n✓ Created {notes_created} notes")
    if notes_failed > 0:
        print(f"⚠️  Failed to create {notes_failed} notes")
    
    # Create package
    print(f"\n📦 Packaging deck with {len(media_files)} audio files...")
    package = genanki.Package(deck)
    package.media_files = media_files
    
    # Write package
    print(f"\n💾 Writing to {output_file}...")
    package.write_to_file(output_file)
    
    # Summary
    print("\n" + "="*60)
    print("✅ SUCCESS! Anki deck created!")
    print("="*60)
    print(f"📦 Output file: {output_file}")
    print(f"📊 Total notes: {notes_created}")
    print(f"🔊 Audio files: {len(media_files)}")
    print(f"🏷️  Deck name: {deck_name}")
    
    # File size
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # Convert to MB
        print(f"📏 Package size: {file_size:.2f} MB")
    
    print("\n" + "="*60)
    print("Next steps:")
    print("="*60)
    print("1. Open Anki")
    print("2. File → Import")
    print(f"3. Select: {os.path.abspath(output_file)}")
    print("4. Click 'Import'")
    print("5. Start learning! 🎉")
    print("\nThe deck includes:")
    print("  • Vietnamese word with audio")
    print("  • English definition")
    print("  • Example sentence in Vietnamese")
    print("  • English translation")
    print("  • Part of speech")


def main():
    """Main entry point."""
    import sys
    
    # Check if enriched data exists
    if not os.path.exists("enriched_deck_data.csv"):
        print("❌ Error: enriched_deck_data.csv not found")
        print("\nPlease run the pipeline in order:")
        print("  1. python 1_generate_list.py")
        print("  2. python 2_enrich_data.py")
        print("  3. python 3_synthesize_audio.py")
        print("  4. python 4_create_apkg.py  ← You are here")
        sys.exit(1)
    
    # Check if audio directory exists
    if not os.path.exists("audio"):
        print("⚠️  Warning: audio/ directory not found")
        response = input("Continue without audio files? (y/n): ")
        if response.lower() != 'y':
            print("Please run: python 3_synthesize_audio.py")
            sys.exit(1)
    
    create_anki_deck(
        input_file="enriched_deck_data.csv",
        audio_dir="audio",
        output_file="Vietnamese_Core_2000.apkg",
        deck_name="Vietnamese Core 2000",
        deck_description="Top 2000 most frequent Vietnamese words with audio, definitions, and examples. Generated with AI-powered content."
    )


if __name__ == "__main__":
    main()

