#!/usr/bin/env python3
"""
Fix bound morphemes in the Vietnamese vocabulary deck.

For words that can't stand alone (bound morphemes), this script:
1. Identifies all common compound forms using Gemini
2. Creates separate entries for compounds with different meanings
3. Merges compounds with same meaning into one entry (alternatives on back)
4. Masks Vietnamese words in usage notes with [English] equivalents
"""

import csv
import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def setup_gemini():
    """Configure Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def create_identification_prompt(entries):
    """Create prompt to identify bound morphemes."""
    entries_text = "\n".join([
        f"- {e['lemma']}: {e['pos']} - \"{e['definition']}\""
        for e in entries
    ])
    
    return f"""You are a Vietnamese linguistics expert. Review these entries and identify BOUND MORPHEMES - words that are rarely/never used alone in modern Vietnamese.

ENTRIES:
{entries_text}

ONLY flag words that genuinely CANNOT stand alone in normal speech:
- "ta" (we) → archaic alone, needs "chúng ta"
- "thế" (how/that) → needs "thế nào" or "như thế"
- Many Sino-Vietnamese roots DO work alone - don't over-flag

For each BOUND MORPHEME found, list ALL common compound forms with their distinct meanings.

Format as JSON:
```json
[
  {{
    "lemma": "thế₁",
    "is_bound": true,
    "compounds": [
      {{"form": "thế nào", "meaning": "how, in what way"}},
      {{"form": "như thế", "meaning": "like that, so"}}
    ]
  }},
  {{
    "lemma": "ta₁", 
    "is_bound": true,
    "compounds": [
      {{"form": "chúng ta", "meaning": "we, us (inclusive)"}}
    ]
  }}
]
```

If NO bound morphemes in this batch, return: []

Only return JSON."""

def create_expansion_prompt(lemma, definition, pos):
    """Create prompt to expand a single bound morpheme into compounds."""
    return f"""You are a Vietnamese linguistics expert.

The word "{lemma}" ({pos}: "{definition}") is a bound morpheme - it cannot stand alone in modern Vietnamese.

List ALL common compound words that use "{lemma}" with their distinct meanings.

Group compounds by meaning - if two compounds mean the same thing, put them together.

Format as JSON:
```json
{{
  "lemma": "{lemma}",
  "compound_groups": [
    {{
      "meaning": "how, in what way",
      "primary_form": "thế nào",
      "alternative_forms": ["làm sao"],
      "pos": "adverb",
      "example_vi": "Thế nào rồi?",
      "example_en": "How is it going?"
    }},
    {{
      "meaning": "like that, so, thus",
      "primary_form": "như thế",
      "alternative_forms": ["như vậy"],
      "pos": "adverb", 
      "example_vi": "Như thế là đúng.",
      "example_en": "Like that is correct."
    }}
  ]
}}
```

Only return JSON."""

def parse_gemini_response(response_text):
    """Parse Gemini's JSON response."""
    text = response_text.strip()
    
    # Remove markdown code blocks
    if text.startswith('```'):
        lines = text.split('\n')
        lines = [l for l in lines if not l.startswith('```')]
        text = '\n'.join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error: {e}")
        print(f"  Response: {text[:300]}...")
        return None

def identify_bound_morphemes(model, entries, batch_num, total_batches):
    """Identify which entries are bound morphemes."""
    prompt = create_identification_prompt(entries)
    
    print(f"  Batch {batch_num}/{total_batches}: Scanning {len(entries)} entries...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            result = parse_gemini_response(response.text)
            if result:
                bound = [r for r in result if r.get('is_bound', False)]
                if bound:
                    print(f"    → Found {len(bound)} bound morphemes")
                return bound
            return []
        except Exception as e:
            print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return []

def expand_bound_morpheme(model, lemma, definition, pos):
    """Get all compound forms for a bound morpheme."""
    prompt = create_expansion_prompt(lemma, definition, pos)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            result = parse_gemini_response(response.text)
            if result and 'compound_groups' in result:
                return result['compound_groups']
            return None
        except Exception as e:
            print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return None

def mask_vietnamese_in_text(text, word_to_mask, english_replacement):
    """Replace Vietnamese word in text with [English] equivalent."""
    if not text or not word_to_mask:
        return text
    
    # Create pattern that matches the word (case insensitive for Vietnamese)
    pattern = re.compile(re.escape(word_to_mask), re.IGNORECASE)
    masked = pattern.sub(f"[{english_replacement}]", text)
    return masked

def main():
    print("=" * 60)
    print("Fixing Bound Morphemes - Compound Expansion")
    print("=" * 60)
    
    # Setup
    print("\n🤖 Setting up Gemini...")
    model = setup_gemini()
    
    # Read data
    print("\n📖 Reading enriched_deck_data.csv...")
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"✓ Loaded {len(rows)} entries")
    
    # Get single-word entries (potential bound morphemes)
    single_word_entries = []
    for idx, row in enumerate(rows):
        if row.get('Is_Compound', 'False') == 'False':
            # Check if it's not already a multi-word
            lemma = row.get('original_word', row.get('lemma', ''))
            if ' ' not in lemma:
                single_word_entries.append({
                    'lemma': row.get('lemma', ''),
                    'original_word': lemma,
                    'pos': row.get('pos', ''),
                    'definition': row.get('english_definition', ''),
                    'row_index': idx
                })
    
    print(f"📝 Found {len(single_word_entries)} single-word entries to scan")
    
    # Phase 1: Identify bound morphemes
    print("\n🔍 Phase 1: Identifying bound morphemes...")
    batch_size = 40
    all_bound = []
    total_batches = (len(single_word_entries) + batch_size - 1) // batch_size
    
    for i in range(0, len(single_word_entries), batch_size):
        batch = single_word_entries[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        bound = identify_bound_morphemes(model, batch, batch_num, total_batches)
        
        # Match back to row indices
        for b in bound:
            for entry in batch:
                if entry['lemma'] == b['lemma']:
                    b['row_index'] = entry['row_index']
                    b['original_word'] = entry['original_word']
                    b['definition'] = entry['definition']
                    b['pos'] = entry['pos']
                    break
            all_bound.append(b)
        
        if i + batch_size < len(single_word_entries):
            time.sleep(0.3)
    
    print(f"\n✓ Found {len(all_bound)} bound morphemes total")
    
    if not all_bound:
        print("No bound morphemes found!")
        return
    
    # Phase 2: Expand each bound morpheme to compound forms
    print("\n🔄 Phase 2: Expanding bound morphemes to compounds...")
    
    rows_to_remove = set()
    new_rows = []
    
    for i, bound in enumerate(all_bound):
        lemma = bound.get('lemma', '')
        original = bound.get('original_word', lemma)
        definition = bound.get('definition', '')
        pos = bound.get('pos', '')
        row_idx = bound.get('row_index')
        
        print(f"  [{i+1}/{len(all_bound)}] Expanding: {lemma}")
        
        # Check if Gemini already provided compounds
        if 'compounds' in bound and bound['compounds']:
            # Simple case - use what we already have
            compounds = bound['compounds']
            
            for j, comp in enumerate(compounds):
                # Get original row data as template
                orig_row = rows[row_idx].copy() if row_idx is not None else {}
                
                new_row = orig_row.copy()
                new_row['lemma'] = comp['form'] if j == 0 else f"{comp['form']}"
                new_row['original_word'] = comp['form']
                new_row['english_definition'] = comp['meaning']
                new_row['Is_Compound'] = 'True'
                
                # Clear sense info since this is now a compound
                new_row['sense_number'] = '1'
                new_row['total_senses'] = '1'
                
                new_rows.append(new_row)
            
            if row_idx is not None:
                rows_to_remove.add(row_idx)
        else:
            # Need to get full expansion
            compound_groups = expand_bound_morpheme(model, original, definition, pos)
            
            if compound_groups:
                for j, group in enumerate(compound_groups):
                    # Get original row as template
                    orig_row = rows[row_idx].copy() if row_idx is not None else {}
                    
                    primary = group.get('primary_form', '')
                    alternatives = group.get('alternative_forms', [])
                    meaning = group.get('meaning', definition)
                    group_pos = group.get('pos', pos)
                    example_vi = group.get('example_vi', '')
                    example_en = group.get('example_en', '')
                    
                    new_row = orig_row.copy()
                    new_row['lemma'] = primary
                    new_row['original_word'] = primary
                    new_row['english_definition'] = meaning
                    new_row['pos'] = group_pos
                    new_row['Is_Compound'] = 'True'
                    new_row['sense_number'] = '1'
                    new_row['total_senses'] = '1'
                    
                    if example_vi:
                        new_row['example_vi'] = example_vi
                    if example_en:
                        new_row['example_en'] = example_en
                    
                    # If there are alternative forms, note them
                    if alternatives:
                        alt_text = ", ".join(alternatives)
                        # Mask the Vietnamese in the usage note
                        masked_alts = []
                        for alt in alternatives:
                            masked_alts.append(f"[{meaning.split(',')[0].strip()}]")
                        new_row['Usage_Note'] = f"Also: {alt_text}"
                    
                    new_rows.append(new_row)
                    print(f"    + {primary}: {meaning}")
                
                if row_idx is not None:
                    rows_to_remove.add(row_idx)
            else:
                print(f"    ⚠️ Could not expand {lemma}")
            
            time.sleep(0.3)
    
    # Phase 3: Mask Vietnamese in existing Usage Notes
    print("\n🎭 Phase 3: Masking Vietnamese in usage notes...")
    
    masked_count = 0
    for row in rows:
        usage_note = row.get('Usage_Note', '')
        if usage_note:
            lemma = row.get('original_word', row.get('lemma', ''))
            definition = row.get('english_definition', '')
            
            # Get the first word of the definition as the mask
            first_meaning = definition.split(',')[0].split(';')[0].strip()
            if first_meaning.startswith('to '):
                first_meaning = first_meaning[3:]
            
            # Mask the lemma in the usage note
            if lemma and lemma in usage_note:
                new_note = mask_vietnamese_in_text(usage_note, lemma, first_meaning)
                if new_note != usage_note:
                    row['Usage_Note'] = new_note
                    masked_count += 1
    
    # Also mask in new rows
    for row in new_rows:
        usage_note = row.get('Usage_Note', '')
        if usage_note:
            lemma = row.get('original_word', row.get('lemma', ''))
            definition = row.get('english_definition', '')
            first_meaning = definition.split(',')[0].split(';')[0].strip()
            if first_meaning.startswith('to '):
                first_meaning = first_meaning[3:]
            
            if lemma and lemma in usage_note:
                row['Usage_Note'] = mask_vietnamese_in_text(usage_note, lemma, first_meaning)
    
    print(f"✓ Masked Vietnamese in {masked_count} usage notes")
    
    # Build final rows
    print("\n💾 Building final dataset...")
    
    # Remove old bound morpheme rows
    final_rows = [row for idx, row in enumerate(rows) if idx not in rows_to_remove]
    
    # Add new compound rows
    final_rows.extend(new_rows)
    
    # Re-sort by rank (keeping rank as original)
    def get_rank(row):
        try:
            return int(row.get('Rank', 9999))
        except:
            return 9999
    
    final_rows.sort(key=get_rank)
    
    print(f"✓ Final dataset: {len(final_rows)} entries")
    print(f"  - Removed: {len(rows_to_remove)} bound morphemes")
    print(f"  - Added: {len(new_rows)} compound entries")
    
    # Save
    print("\n💾 Saving to enriched_deck_data.csv...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
    
    print("✓ Saved!")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 Original entries: {len(rows)}")
    print(f"🔧 Bound morphemes fixed: {len(rows_to_remove)}")
    print(f"🆕 New compound entries: {len(new_rows)}")
    print(f"📊 Final entries: {len(final_rows)}")
    print(f"🎭 Usage notes masked: {masked_count}")
    
    print("\n⚠️  Next steps:")
    print("1. Run 3_synthesize_audio.py for new compounds")
    print("2. Run 4_create_apkg.py to regenerate deck")

if __name__ == "__main__":
    main()
