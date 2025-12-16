#!/usr/bin/env python3
"""
Final deck quality fix script.
Fixes: duplicates, malformed POS, wrong POS labels, Vietnamese in usage notes.
"""

import csv
import re
import ast
from collections import defaultdict

def fix_malformed_pos(pos):
    """Fix POS that looks like "['adverb', 'adjective']" -> "adverb, adjective"."""
    if not pos:
        return pos
    
    # Check if it looks like a Python list string
    if pos.startswith('[') and pos.endswith(']'):
        try:
            # Try to parse as Python list
            parsed = ast.literal_eval(pos)
            if isinstance(parsed, list):
                return ', '.join(str(p) for p in parsed)
        except:
            pass
    
    # Also fix "['x', 'y']" patterns
    if pos.startswith("['") or pos.startswith('["'):
        try:
            parsed = ast.literal_eval(pos)
            if isinstance(parsed, list):
                return ', '.join(str(p) for p in parsed)
        except:
            pass
    
    return pos

def fix_known_pos_errors(row):
    """Fix specific known POS errors."""
    lemma = row.get('original_word', row.get('lemma', ''))
    pos = row.get('pos', '')
    
    # Known fixes
    fixes = {
        'hội đồng': 'noun',
        'sử dụng': 'verb',
        'di chuyển': 'verb',
    }
    
    if lemma in fixes and pos not in ['noun', 'verb', 'adjective', 'adverb']:
        row['pos'] = fixes[lemma]
        return True
    
    # Fix "verb root" -> just use the actual POS based on definition
    if pos == 'verb root':
        definition = row.get('english_definition', '').lower()
        if 'to ' in definition:
            row['pos'] = 'verb'
        else:
            row['pos'] = 'noun'
        return True
    
    return False

def mask_vietnamese_in_usage_note(note):
    """Replace Vietnamese words in usage notes with [English] equivalents."""
    if not note:
        return note
    
    # Pattern: Vietnamese word followed by " = English"
    # e.g., "sự thật = the truth" -> "[truth] = the truth"
    pattern = r'([a-zA-ZÀ-ỹ]+(?:\s+[a-zA-ZÀ-ỹ]+)*)\s*=\s*(?:the\s+)?([a-zA-Z\s,]+?)(?=[,.\)]|$)'
    
    def replace_match(m):
        vietnamese = m.group(1)
        english = m.group(2).strip()
        # Get first word of English as the mask
        first_word = english.split(',')[0].split()[0] if english else vietnamese
        return f'[{first_word}] = {english}'
    
    result = re.sub(pattern, replace_match, note)
    return result

def main():
    print("=" * 60)
    print("Final Deck Quality Fix")
    print("=" * 60)
    
    # Read data
    print("\n📖 Reading enriched_deck_data.csv...")
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"✓ Loaded {len(rows)} entries")
    
    # Track fixes
    duplicates_removed = 0
    pos_fixed = 0
    pos_errors_fixed = 0
    notes_masked = 0
    
    # Step 1: Remove duplicates
    print("\n🔍 Step 1: Removing duplicates...")
    seen = set()
    unique_rows = []
    
    for row in rows:
        # Create unique key from word + definition
        key = (row.get('original_word', ''), row.get('english_definition', ''))
        
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
        else:
            duplicates_removed += 1
            print(f"  Removed duplicate: {row.get('original_word', '')} - {row.get('english_definition', '')[:40]}...")
    
    print(f"  ✓ Removed {duplicates_removed} duplicates")
    rows = unique_rows
    
    # Step 2: Fix malformed POS
    print("\n🏷️ Step 2: Fixing malformed POS...")
    for row in rows:
        old_pos = row.get('pos', '')
        new_pos = fix_malformed_pos(old_pos)
        if new_pos != old_pos:
            row['pos'] = new_pos
            pos_fixed += 1
            print(f"  Fixed: {old_pos} -> {new_pos}")
    
    print(f"  ✓ Fixed {pos_fixed} malformed POS entries")
    
    # Step 3: Fix known POS errors
    print("\n🔧 Step 3: Fixing known POS errors...")
    for row in rows:
        if fix_known_pos_errors(row):
            pos_errors_fixed += 1
    
    print(f"  ✓ Fixed {pos_errors_fixed} POS label errors")
    
    # Step 4: Mask Vietnamese in usage notes
    print("\n🎭 Step 4: Masking Vietnamese in usage notes...")
    for row in rows:
        old_note = row.get('Usage_Note', '')
        if old_note:
            new_note = mask_vietnamese_in_usage_note(old_note)
            if new_note != old_note:
                row['Usage_Note'] = new_note
                notes_masked += 1
    
    print(f"  ✓ Masked Vietnamese in {notes_masked} usage notes")
    
    # Step 5: Re-number ranks
    print("\n📈 Step 5: Re-numbering ranks...")
    for i, row in enumerate(rows):
        row['Rank'] = str(i + 1)
    
    print(f"  ✓ Assigned ranks 1 to {len(rows)}")
    
    # Step 6: Verify no duplicates remain
    print("\n✅ Step 6: Verifying no duplicates...")
    check_keys = set()
    duplicate_check = False
    for row in rows:
        key = (row.get('original_word', ''), row.get('english_definition', ''))
        if key in check_keys:
            print(f"  ⚠️ Still duplicate: {key[0]}")
            duplicate_check = True
        check_keys.add(key)
    
    if not duplicate_check:
        print("  ✓ No duplicates found!")
    
    # Save
    print("\n💾 Saving cleaned data...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Saved {len(rows)} entries")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 Final entries: {len(rows)}")
    print(f"🗑️ Duplicates removed: {duplicates_removed}")
    print(f"🏷️ Malformed POS fixed: {pos_fixed}")
    print(f"🔧 POS errors fixed: {pos_errors_fixed}")
    print(f"🎭 Usage notes masked: {notes_masked}")

if __name__ == "__main__":
    main()

