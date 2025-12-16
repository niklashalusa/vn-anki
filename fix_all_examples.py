#!/usr/bin/env python3
"""
Aggressively fix ALL compound examples to ensure they match.
"""

import csv
import json
import os
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def setup_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def example_matches(row):
    """Check if example actually contains the word."""
    lemma = row.get('original_word', row.get('lemma', ''))
    example = row.get('example_vi', '')
    
    if not example:
        return False
    
    # Clean lemma
    clean = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)
    
    # Skip pattern cards
    if 'V +' in clean or 'N +' in clean or '+ V' in clean or '+ N' in clean:
        return True
    
    clean = clean.strip().lower()
    example_lower = example.lower()
    
    # Direct match
    if clean in example_lower:
        return True
    
    # For compounds, require all parts
    parts = clean.split()
    if len(parts) > 1:
        return all(p in example_lower for p in parts if len(p) > 1)
    
    return False

def create_batch_prompt(entries):
    """Create prompt for batch example generation."""
    entries_text = "\n".join([
        f"- {e['lemma']} ({e['pos']}): \"{e['definition']}\""
        for e in entries
    ])
    
    return f"""Generate simple Vietnamese example sentences. Each example MUST contain the EXACT word/phrase listed.

WORDS:
{entries_text}

Requirements:
- Example must contain the exact Vietnamese word
- Keep sentences simple (A1-A2 level)
- Make examples natural and useful

Format as JSON array:
```json
[{{"lemma": "thể hiện", "example_vi": "Anh ấy thể hiện tình cảm qua hành động.", "example_en": "He expresses his feelings through actions."}}]
```

Only return JSON."""

def main():
    print("=" * 60)
    print("Fixing ALL Mismatched Examples")
    print("=" * 60)
    
    model = setup_gemini()
    
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"✓ Loaded {len(rows)} entries")
    
    # Find ALL mismatched examples
    to_fix = []
    for idx, row in enumerate(rows):
        if not example_matches(row):
            to_fix.append({
                'idx': idx,
                'lemma': row.get('original_word', row.get('lemma', '')),
                'pos': row.get('pos', ''),
                'definition': row.get('english_definition', '')
            })
    
    print(f"📝 Found {len(to_fix)} entries needing new examples")
    
    if not to_fix:
        print("All examples match!")
        return
    
    # Process in batches
    batch_size = 25
    fixes_applied = 0
    
    for i in range(0, len(to_fix), batch_size):
        batch = to_fix[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(to_fix) + batch_size - 1) // batch_size
        print(f"\n  Batch {batch_num}/{total_batches}: Generating {len(batch)} examples...")
        
        prompt = create_batch_prompt(batch)
        
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith('```'):
                lines = text.split('\n')
                lines = [l for l in lines if not l.startswith('```')]
                text = '\n'.join(lines)
            
            results = json.loads(text)
            
            for result in results:
                lemma = result.get('lemma', '')
                example_vi = result.get('example_vi', '')
                example_en = result.get('example_en', '')
                
                for entry in batch:
                    if entry['lemma'] == lemma or entry['lemma'].replace('₁','').replace('₂','').replace('₃','') == lemma:
                        idx = entry['idx']
                        if example_vi:
                            rows[idx]['example_vi'] = example_vi
                            rows[idx]['example_en'] = example_en
                            fixes_applied += 1
                        break
            
            print(f"    ✓ Fixed {len([r for r in results if r.get('example_vi')])}")
            
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
        
        time.sleep(0.3)
    
    # Save
    print(f"\n💾 Saving {fixes_applied} fixes...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Done! Fixed {fixes_applied} examples.")

if __name__ == "__main__":
    main()

