#!/usr/bin/env python3
"""
Merge over-split polysemy entries.

Some words are unnecessarily split into multiple senses when they could be
combined into a single entry (e.g., biết₁ "to know fact" + biết₂ "to know how"
→ just "to know").

Only merges entries where:
1. Same or similar POS
2. Definitions are synonymous or contextual variants
3. A learner would recognize them as "the same word"
"""

import csv
import json
import os
import re
import time
from collections import defaultdict
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

def get_base_word(lemma):
    """Get base word without subscript."""
    return re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)

def create_merge_prompt(word_groups):
    """Create prompt to identify which senses should be merged."""
    groups_text = ""
    for base_word, senses in word_groups.items():
        groups_text += f"\n{base_word}:\n"
        for s in senses:
            groups_text += f"  - {s['lemma']} ({s['pos']}): \"{s['definition']}\"\n"
    
    return f"""You are a Vietnamese language expert. Be VERY CONSERVATIVE about merging.

Review these word pairs. ONLY merge if ALL criteria are met:

STRICT MERGE CRITERIA (ALL must be true):
1. EXACT same part of speech (verb+verb, noun+noun, etc.)
2. Meanings are SYNONYMOUS (not just "related")
3. The English translation would be essentially IDENTICAL
4. A standard dictionary would list them as ONE entry, not two

DEFAULT TO "keep" - when in doubt, keep separate!

MUST KEEP SEPARATE:
- Different POS (noun vs verb, preposition vs verb, adj vs adverb)
- Different core meanings (even if related)
- "to see" vs "to feel" = KEEP (different senses)
- "to appear" vs "to export" = KEEP (different meanings)
- "with" (prep) vs "to reach" (verb) = KEEP (different POS)

ONLY MERGE examples:
- "to know (a fact)" + "to know (how to)" = MERGE (same verb, synonymous)
- "also, too" + "as well" = MERGE (same meaning)

WORD GROUPS:
{groups_text}

Respond with JSON. Use "keep" for most entries:
```json
[
  {{
    "base_word": "biết",
    "action": "merge",
    "merged_definition": "to know; to know how to",
    "merged_pos": "verb",
    "reason": "Exact same verb, synonymous meanings"
  }},
  {{
    "base_word": "thấy",
    "action": "keep",
    "reason": "Different senses: visual perception vs emotional feeling"
  }}
]
```

Only return the JSON array."""

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
    print("Merging Over-Split Polysemy Entries")
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
    
    # Group entries by base word
    word_groups = defaultdict(list)
    for i, row in enumerate(rows):
        lemma = row.get('lemma', '')
        base = get_base_word(lemma)
        total_senses = int(row.get('total_senses', 1))
        
        # Only consider words with exactly 2 senses (most likely over-split)
        if total_senses == 2:
            word_groups[base].append({
                'index': i,
                'lemma': lemma,
                'pos': row.get('pos', ''),
                'definition': row.get('english_definition', ''),
                'example_vi': row.get('example_vi', ''),
                'example_en': row.get('example_en', ''),
                'row': row
            })
    
    # Filter to only complete groups (have both senses)
    complete_groups = {k: v for k, v in word_groups.items() if len(v) == 2}
    
    print(f"📝 Found {len(complete_groups)} words with exactly 2 senses")
    
    if not complete_groups:
        print("No merge candidates found!")
        return
    
    # Process in batches
    batch_size = 25
    group_items = list(complete_groups.items())
    all_decisions = {}
    total_batches = (len(group_items) + batch_size - 1) // batch_size
    
    print(f"\n🔍 Analyzing merge candidates in {total_batches} batches...")
    
    for i in range(0, len(group_items), batch_size):
        batch = dict(group_items[i:i + batch_size])
        batch_num = (i // batch_size) + 1
        
        print(f"  Batch {batch_num}/{total_batches}: Analyzing {len(batch)} word groups...")
        
        prompt = create_merge_prompt(batch)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                decisions = parse_response(response.text)
                
                for d in decisions:
                    base = d.get('base_word', '')
                    if base:
                        all_decisions[base] = d
                
                merge_count = len([d for d in decisions if d.get('action') == 'merge'])
                print(f"    → Merge: {merge_count}, Keep: {len(decisions) - merge_count}")
                break
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        if i + batch_size < len(group_items):
            time.sleep(0.5)
    
    # Apply merges
    print(f"\n💾 Applying merge decisions...")
    
    merge_decisions = {k: v for k, v in all_decisions.items() if v.get('action') == 'merge'}
    print(f"📊 Words to merge: {len(merge_decisions)}")
    
    # Track which rows to remove and which to update
    rows_to_remove = set()
    merges_applied = 0
    
    for base_word, decision in merge_decisions.items():
        if base_word not in complete_groups:
            continue
        
        senses = complete_groups[base_word]
        if len(senses) != 2:
            continue
        
        # Keep first sense, merge into it
        first = senses[0]
        second = senses[1]
        
        # Update first sense with merged data
        first_row = rows[first['index']]
        first_row['lemma'] = base_word  # Remove subscript
        first_row['english_definition'] = decision.get('merged_definition', first['definition'])
        first_row['pos'] = decision.get('merged_pos', first['pos'])
        first_row['sense_number'] = '1'
        first_row['total_senses'] = '1'
        
        # Mark second sense for removal
        rows_to_remove.add(second['index'])
        merges_applied += 1
    
    print(f"✓ Merged {merges_applied} word pairs")
    print(f"🗑️  Removing {len(rows_to_remove)} duplicate entries")
    
    # Remove duplicate rows
    new_rows = [row for i, row in enumerate(rows) if i not in rows_to_remove]
    
    print(f"📊 Entries before: {len(rows)}, after: {len(new_rows)}")
    
    # Save
    print("\n💾 Writing updated data...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
    
    print(f"✓ Saved {len(new_rows)} entries to enriched_deck_data.csv")
    
    # Show samples
    print("\n📋 Sample merges:")
    sample_count = 0
    for base, decision in list(merge_decisions.items())[:5]:
        print(f"  • {base}: {decision.get('merged_definition', 'N/A')[:60]}...")
        print(f"    Reason: {decision.get('reason', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 2-sense word groups analyzed: {len(complete_groups)}")
    print(f"✅ Merges applied: {merges_applied}")
    print(f"🗑️  Entries removed: {len(rows_to_remove)}")
    print(f"📦 Final entry count: {len(new_rows)}")

if __name__ == "__main__":
    main()

