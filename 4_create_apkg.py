#!/usr/bin/env python3
"""
Create Anki deck package (.apkg) from enriched Vietnamese word data.

This script reads the enriched CSV data and audio files, then generates
a complete Anki deck package ready for import.

Handles polysemy notation (để₁, để₂) by displaying the sense number
as a superscript on the card.

Output: Vietnamese_Core_2000.apkg
"""

import csv
import os
import re
from pathlib import Path
import genanki
import random


def format_lemma_display(lemma: str) -> str:
    """
    Format lemma for display, converting subscript numbers to superscript HTML.
    
    Example: để₁ → để<sup>1</sup>
    """
    # Map subscript digits to regular digits
    subscript_map = {
        '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
        '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'
    }
    
    result = lemma
    for sub, digit in subscript_map.items():
        if sub in result:
            result = result.replace(sub, f'<sup>{digit}</sup>')
    
    return result


def get_base_word(lemma: str) -> str:
    """
    Get the base word without sense subscripts.
    
    Example: để₁ → để
    """
    # Remove subscript digits
    return re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)


# Define custom Anki Note Model
VIETNAMESE_MODEL = genanki.Model(
    1607392319,  # Unique model ID (random, but consistent)
    'Vietnamese Core Vocabulary',
    fields=[
        {'name': 'Lemma'},
        {'name': 'LemmaDisplay'},  # HTML formatted version
        {'name': 'Definition'},
        {'name': 'Audio'},
        {'name': 'Sentence_VI'},
        {'name': 'Sentence_EN'},
        {'name': 'POS'},
        {'name': 'UsageNote'},  # Practical grammar guidance
    ],
    templates=[
        {
            'name': 'English → Vietnamese (Recall)',
            'qfmt': '''
                <div class="card">
                    <div class="definition">{{Definition}}</div>
                    <div class="pos">{{POS}}</div>
                    {{#UsageNote}}<div class="usage-note">{{UsageNote}}</div>{{/UsageNote}}
                </div>
            ''',
            'afmt': '''
                <div class="card">
                    <div class="definition-small">{{Definition}}</div>
                    <hr id="answer">
                    <div class="lemma">{{LemmaDisplay}}</div>
                    <div class="audio">{{Audio}}</div>
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
            font-size: 36px;
            font-weight: bold;
            color: #333;
            margin: 30px 0;
            padding: 20px;
            line-height: 1.3;
        }
        
        .definition-small {
            font-size: 18px;
            color: #666;
            margin: 10px 0;
        }
        
        .usage-note {
            font-size: 16px;
            color: #555;
            margin: 15px 0;
            padding: 12px;
            background-color: #e8f5e9;
            border-radius: 6px;
            border-left: 3px solid #4CAF50;
            text-align: left;
            font-style: italic;
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
        
        .lemma sup {
            font-size: 0.5em;
            color: #999;
            vertical-align: super;
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
    print(f"\n📝 Creating Anki notes with frequency tags...")
    notes_created = 0
    notes_failed = 0
    polysemy_count = 0
    
    for i, word in enumerate(words, 1):
        try:
            rank = word.get('Rank', '')
            lemma = word.get('lemma', '')
            original_word = word.get('original_word', lemma)
            sense_number = word.get('sense_number', '1')
            total_senses = word.get('total_senses', '1')
            definition = word.get('english_definition', '')
            pos = word.get('pos', '')
            sentence_vi = word.get('example_vi', '')
            sentence_en = word.get('example_en', '')
            audio_path_str = word.get('Audio_Path', '')
            usage_note = word.get('Usage_Note', '')
            
            # Skip if essential data is missing
            if not lemma or not definition:
                print(f"⚠️  Skipping word {rank}: Missing essential data")
                notes_failed += 1
                continue
            
            # Skip entries marked for review
            if definition == '[needs review]':
                print(f"⚠️  Skipping word {rank} ({lemma}): Needs review")
                notes_failed += 1
                continue
            
            # Format lemma for display (convert subscripts to superscripts)
            lemma_display = format_lemma_display(lemma)
            
            # Track polysemy for stats
            try:
                if int(total_senses) > 1:
                    polysemy_count += 1
            except:
                pass
            
            # Get base word for audio file lookup
            base_word = get_base_word(lemma)
            
            # Look for audio file (may be based on original_word or base_word)
            audio_anki_format = ""
            for audio_base in [original_word, base_word, lemma]:
                if not audio_base:
                    continue
                # Sanitize for filename
                safe_name = audio_base.replace(' ', '_').replace('/', '_')
                audio_filename = f"{rank}_{safe_name}.mp3"
                full_audio_path = audio_path / audio_filename
                
                if full_audio_path.exists():
                    audio_anki_format = f"[sound:{audio_filename}]"
                    if str(full_audio_path) not in media_files:
                        media_files.append(str(full_audio_path))
                    break
            
            # Also check for audio path in CSV
            if not audio_anki_format and audio_path_str:
                if audio_path_str.startswith('[sound:') and audio_path_str.endswith(']'):
                    audio_filename = audio_path_str[7:-1]
                    full_audio_path = audio_path / audio_filename
                    if full_audio_path.exists():
                        audio_anki_format = audio_path_str
                        if str(full_audio_path) not in media_files:
                            media_files.append(str(full_audio_path))
            
            # Calculate frequency bucket tag (Anki tags cannot contain spaces)
            try:
                rank_num = int(rank)
                bucket_start = ((rank_num - 1) // 100) * 100 + 1
                bucket_end = bucket_start + 99
                frequency_tag = f"{bucket_start}-{bucket_end}_Most_Frequent"
                tags = ['vietnamese', 'core-vocabulary', frequency_tag]
            except ValueError:
                # If rank isn't a number, use default tags
                tags = ['vietnamese', 'core-vocabulary']
            
            # Create note with field structure
            note = genanki.Note(
                model=VIETNAMESE_MODEL,
                fields=[
                    lemma,           # Lemma (raw)
                    lemma_display,   # LemmaDisplay (HTML formatted)
                    definition,      # Definition
                    audio_anki_format,  # Audio
                    sentence_vi,     # Sentence_VI
                    sentence_en,     # Sentence_EN
                    pos,             # POS
                    usage_note,      # UsageNote (grammar guidance)
                ],
                tags=tags
            )
            
            # Add to main deck
            deck.add_note(note)
            notes_created += 1
            
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(words)} words processed...")
            
        except Exception as e:
            print(f"❌ Error creating note for word {i}: {e}")
            notes_failed += 1
    
    print(f"\n✓ Created {notes_created} notes")
    print(f"🏷️  Tagged with frequency buckets (100 words per bucket)")
    if polysemy_count > 0:
        print(f"🔀 Including {polysemy_count} polysemy entries")
    if notes_failed > 0:
        print(f"⚠️  Failed to create {notes_failed} notes")
    
    # Create package with main deck
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
    print(f"🏷️  Deck name: {deck_name}")
    print(f"🔖 Tagged by frequency buckets (100 words per tag)")
    print(f"🔊 Audio files: {len(media_files)}")
    
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

