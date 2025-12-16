#!/usr/bin/env python3
"""
Add practical usage notes for technical/grammatical words.

Words with technical definitions like "nominalizing prefix" or "plural marker"
need practical guidance that helps learners understand how to use them.
"""

import csv
import json
import os
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Technical POS types that need usage notes
TECHNICAL_POS = [
    'particle', 'marker', 'prefix', 'suffix', 'classifier',
    'auxiliary', 'determiner', 'passive marker', 'modal'
]

def setup_gemini():
    """Configure Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def needs_usage_note(row):
    """Check if entry needs a usage note based on POS."""
    pos = row.get('pos', '').lower()
    definition = row.get('english_definition', '').lower()
    
    # Check if POS contains technical terms
    for term in TECHNICAL_POS:
        if term in pos:
            return True
    
    # Check if definition contains technical jargon
    jargon = ['marker', 'prefix', 'suffix', 'nominaliz', 'classifier', 'particle']
    for j in jargon:
        if j in definition:
            return True
    
    return False

def create_usage_note_prompt(entries):
    """Create prompt for Gemini to generate usage notes."""
    entries_text = "\n".join([
        f"- {e['lemma']} ({e['pos']}): \"{e['definition']}\" | Example: {e['example_vi']}"
        for e in entries
    ])
    
    return f"""You are a Vietnamese language teacher creating practical usage notes for learners.

For each word below, write a SHORT, PRACTICAL usage note that explains:
1. WHERE to place the word in a sentence
2. WHAT it does grammatically
3. 1-2 EXAMPLE patterns (in format: Vietnamese = English)

IMPORTANT:
- Be concise (max 2 sentences + examples)
- Use simple English, avoid linguistic jargon
- Focus on practical patterns learners can copy
- If the word is already clear from its definition, write "null"

ENTRIES:
{entries_text}

Respond with a JSON array:
```json
[
  {{
    "lemma": "sự",
    "usage_note": "Place before verbs to make abstract nouns. Examples: sự thật = the truth, sự việc = the matter"
  }},
  {{
    "lemma": "những",
    "usage_note": "Place before nouns to indicate plural. Examples: những người = the people, những ngày = the days"
  }},
  {{
    "lemma": "đi",
    "usage_note": null
  }}
]
```

Only return the JSON array, no other text."""

def parse_response(response_text):
    """Parse Gemini's JSON response."""
    text = response_text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        lines = [l for l in lines if not l.startswith('```')]
        text = '\n'.join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error: {e}")
        return []

def main():
    print("=" * 60)
    print("Adding Usage Notes for Technical Words")
    print("=" * 60)
    
    # Setup
    print("\n🤖 Setting up Gemini...")
    model = setup_gemini()
    
    # Read data
    print("\n📖 Reading enriched_deck_data.csv...")
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)
    
    # Add Usage_Note field if not present
    if 'Usage_Note' not in fieldnames:
        fieldnames.append('Usage_Note')
    
    print(f"✓ Loaded {len(rows)} entries")
    
    # Find entries needing usage notes
    technical_entries = []
    for i, row in enumerate(rows):
        if needs_usage_note(row):
            technical_entries.append({
                'index': i,
                'lemma': row.get('lemma', ''),
                'pos': row.get('pos', ''),
                'definition': row.get('english_definition', ''),
                'example_vi': row.get('example_vi', '')
            })
    
    print(f"📝 Found {len(technical_entries)} technical entries needing usage notes")
    
    if not technical_entries:
        print("No technical entries found!")
        return
    
    # Process in batches
    batch_size = 30
    all_notes = {}
    total_batches = (len(technical_entries) + batch_size - 1) // batch_size
    
    print(f"\n🔍 Generating usage notes in {total_batches} batches...")
    
    for i in range(0, len(technical_entries), batch_size):
        batch = technical_entries[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"  Batch {batch_num}/{total_batches}: Processing {len(batch)} entries...")
        
        prompt = create_usage_note_prompt(batch)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                notes = parse_response(response.text)
                
                for note in notes:
                    lemma = note.get('lemma', '')
                    usage = note.get('usage_note')
                    if lemma and usage:
                        all_notes[lemma] = usage
                
                print(f"    → Generated {len([n for n in notes if n.get('usage_note')])} notes")
                break
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        if i + batch_size < len(technical_entries):
            time.sleep(0.5)
    
    print(f"\n✓ Generated {len(all_notes)} usage notes")
    
    # Apply notes to rows
    print("\n💾 Applying usage notes...")
    notes_applied = 0
    
    for row in rows:
        lemma = row.get('lemma', '')
        if lemma in all_notes:
            row['Usage_Note'] = all_notes[lemma]
            notes_applied += 1
        elif 'Usage_Note' not in row:
            row['Usage_Note'] = ''
    
    print(f"✓ Applied {notes_applied} usage notes")
    
    # Save
    print("\n💾 Writing updated data...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Saved to enriched_deck_data.csv")
    
    # Show samples
    print("\n📋 Sample usage notes:")
    sample_count = 0
    for row in rows:
        if row.get('Usage_Note') and sample_count < 5:
            print(f"  • {row['lemma']}: {row['Usage_Note'][:80]}...")
            sample_count += 1
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 Technical entries found: {len(technical_entries)}")
    print(f"✅ Usage notes generated: {len(all_notes)}")
    print(f"💾 Notes applied: {notes_applied}")

if __name__ == "__main__":
    main()

