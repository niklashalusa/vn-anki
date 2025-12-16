#!/usr/bin/env python3
"""
Fix mismatched example sentences using Gemini.
"""

import csv
import json
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def setup_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def needs_new_example(row):
    """Check if example sentence matches the lemma."""
    lemma = row.get('original_word', row.get('lemma', ''))
    example = row.get('example_vi', '')
    
    if not example or example == '...':
        return True
    
    # Clean lemma
    clean = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)
    clean = re.sub(r'[VNS]\s*\+\s*|\s*\+\s*[VNS]|\[Clause\]\s*\+\s*|\s*\+\s*\[Clause\]', '', clean).strip()
    
    if not clean:
        return False
    
    # Check if lemma appears in example
    if clean.lower() in example.lower():
        return False
    
    # For compounds, check parts
    parts = clean.split()
    if any(part.lower() in example.lower() for part in parts if len(part) > 1):
        return False
    
    return True

def create_example_prompt(entries):
    """Create prompt to generate examples."""
    entries_text = "\n".join([
        f"- {e['lemma']} ({e['pos']}): \"{e['definition']}\""
        for e in entries
    ])
    
    return f"""Generate simple Vietnamese example sentences for these words.
Each example MUST contain the exact word listed.

WORDS:
{entries_text}

Format as JSON:
```json
[
  {{"lemma": "kết bạn", "example_vi": "Tôi muốn kết bạn với cô ấy.", "example_en": "I want to make friends with her."}}
]
```

Keep examples simple (A1-A2 level). Only return JSON."""

def main():
    print("=" * 60)
    print("Fixing Mismatched Example Sentences")
    print("=" * 60)
    
    model = setup_gemini()
    
    # Read data
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"✓ Loaded {len(rows)} entries")
    
    # Find entries needing new examples
    to_fix = []
    for idx, row in enumerate(rows):
        if needs_new_example(row):
            to_fix.append({
                'idx': idx,
                'lemma': row.get('original_word', row.get('lemma', '')),
                'pos': row.get('pos', ''),
                'definition': row.get('english_definition', '')
            })
    
    print(f"📝 Found {len(to_fix)} entries needing new examples")
    
    if not to_fix:
        print("Nothing to fix!")
        return
    
    # Process in batches
    batch_size = 20
    fixes_applied = 0
    
    for i in range(0, len(to_fix), batch_size):
        batch = to_fix[i:i + batch_size]
        print(f"\n  Batch {i//batch_size + 1}: Generating {len(batch)} examples...")
        
        prompt = create_example_prompt(batch)
        
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Parse JSON
            if text.startswith('```'):
                lines = text.split('\n')
                lines = [l for l in lines if not l.startswith('```')]
                text = '\n'.join(lines)
            
            results = json.loads(text)
            
            # Apply fixes
            for result in results:
                lemma = result.get('lemma', '')
                example_vi = result.get('example_vi', '')
                example_en = result.get('example_en', '')
                
                # Find matching entry
                for entry in batch:
                    if entry['lemma'] == lemma:
                        idx = entry['idx']
                        rows[idx]['example_vi'] = example_vi
                        rows[idx]['example_en'] = example_en
                        fixes_applied += 1
                        print(f"    ✓ {lemma}: {example_vi[:40]}...")
                        break
        
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
    
    # Save
    print(f"\n💾 Saving {fixes_applied} fixes...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Done! Fixed {fixes_applied} examples.")

if __name__ == "__main__":
    main()

