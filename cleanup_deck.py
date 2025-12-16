#!/usr/bin/env python3
"""
Cleanup script to fix over-expanded deck issues:
1. Limit compound expansions to top 2 most useful per base word
2. Re-rank ALL entries using wordfreq (compounds too)
3. Fix example sentences to match compounds
4. Consolidate duplicate pattern cards
5. Fix POS labels
6. Target exactly 2000 entries
"""

import csv
import json
import os
import re
from collections import defaultdict
from wordfreq import zipf_frequency
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

def get_frequency_score(word):
    """Get zipf frequency for a word/compound."""
    # Clean the word (remove subscripts, etc.)
    clean = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', word)
    score = zipf_frequency(clean, 'vi')
    return score

def is_pattern_card(lemma):
    """Check if this is a grammar pattern card like 'V + được' or 'N + này'."""
    pattern_indicators = [
        'V +', 'N +', '+ V', '+ N', '[Clause]', 
        'Adj +', '+ Adj', 'S +', '+ S'
    ]
    return any(ind in lemma for ind in pattern_indicators)

def get_base_from_compound(lemma):
    """Extract base morpheme from compound entries sharing same rank."""
    # Remove subscripts
    clean = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)
    return clean

def main():
    print("=" * 60)
    print("Deck Cleanup - Fixing Over-Expansion Issues")
    print("=" * 60)
    
    # Read current data
    print("\n📖 Reading enriched_deck_data.csv...")
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"✓ Loaded {len(rows)} entries (way too many!)")
    
    # Step 1: Group entries by their original rank
    print("\n🔍 Step 1: Analyzing compound groups...")
    rank_groups = defaultdict(list)
    for row in rows:
        rank = row.get('Rank', '9999')
        rank_groups[rank].append(row)
    
    # Find over-expanded groups (more than 3 entries per rank)
    overexpanded = {k: v for k, v in rank_groups.items() if len(v) > 3}
    print(f"  Found {len(overexpanded)} over-expanded groups")
    
    # Step 2: Score ALL entries with wordfreq
    print("\n📊 Step 2: Re-scoring all entries with wordfreq...")
    for row in rows:
        lemma = row.get('original_word', row.get('lemma', ''))
        # Get actual frequency
        freq = get_frequency_score(lemma)
        row['Frequency_Score'] = str(round(freq, 2))
    
    # Step 3: For each over-expanded group, keep only top 2 by frequency
    print("\n✂️ Step 3: Trimming over-expanded groups to top 2...")
    rows_to_keep = []
    trimmed_count = 0
    
    for rank, group in rank_groups.items():
        if len(group) <= 3:
            # Keep all entries in small groups
            rows_to_keep.extend(group)
        else:
            # Sort by actual frequency and keep top 2
            # Also always keep the base word if it exists
            base_entries = []
            compound_entries = []
            pattern_entries = []
            
            for entry in group:
                lemma = entry.get('lemma', '')
                if is_pattern_card(lemma):
                    pattern_entries.append(entry)
                elif entry.get('Is_Compound', 'False') == 'False':
                    base_entries.append(entry)
                else:
                    compound_entries.append(entry)
            
            # Sort compounds by frequency
            compound_entries.sort(
                key=lambda x: float(x.get('Frequency_Score', '0')), 
                reverse=True
            )
            
            # Keep: all base entries + top 1 pattern + top 2 compounds
            kept = base_entries.copy()
            
            # Keep at most 1 pattern card per group
            if pattern_entries:
                kept.append(pattern_entries[0])
            
            # Keep top 2 compounds
            kept.extend(compound_entries[:2])
            
            rows_to_keep.extend(kept)
            trimmed_count += len(group) - len(kept)
            
            if len(group) > 5:
                base_word = base_entries[0].get('original_word', '?') if base_entries else '?'
                print(f"    {base_word}: {len(group)} → {len(kept)} entries")
    
    print(f"  Trimmed {trimmed_count} entries")
    
    # Step 4: Consolidate duplicate pattern cards
    print("\n🔗 Step 4: Consolidating duplicate pattern cards...")
    
    # Group pattern cards by their base pattern
    pattern_groups = defaultdict(list)
    non_pattern_rows = []
    
    for row in rows_to_keep:
        lemma = row.get('lemma', '')
        if is_pattern_card(lemma):
            # Extract the pattern type (e.g., "V + được" and "được + V" are related)
            # Group by the non-pattern word
            clean = re.sub(r'[VNS]\s*\+\s*|\s*\+\s*[VNS]|\[Clause\]\s*\+\s*|\s*\+\s*\[Clause\]', '', lemma).strip()
            pattern_groups[clean].append(row)
        else:
            non_pattern_rows.append(row)
    
    # Keep only 1 pattern card per base word
    consolidated_patterns = []
    for base, patterns in pattern_groups.items():
        if patterns:
            # Keep the one with the best definition
            best = max(patterns, key=lambda x: len(x.get('english_definition', '')))
            consolidated_patterns.append(best)
    
    pattern_removed = sum(len(v) for v in pattern_groups.values()) - len(consolidated_patterns)
    print(f"  Consolidated {pattern_removed} duplicate pattern cards")
    
    rows_to_keep = non_pattern_rows + consolidated_patterns
    
    # Step 5: Fix POS labels
    print("\n🏷️ Step 5: Fixing POS labels...")
    pos_fixes = 0
    for row in rows_to_keep:
        pos = row.get('pos', '')
        lemma = row.get('lemma', '')
        
        # Fix "particle" for compound nouns
        if pos == 'particle' and ' ' in row.get('original_word', ''):
            definition = row.get('english_definition', '').lower()
            if 'noun' in definition or any(w in definition for w in ['truth', 'life', 'death', 'career', 'change', 'importance', 'event']):
                row['pos'] = 'noun'
                pos_fixes += 1
        
        # Fix "passive marker" to "verb phrase"
        if pos == 'passive marker':
            row['pos'] = 'verb phrase'
            pos_fixes += 1
        
        # Fix "modal verb" for pattern cards
        if 'modal verb' in pos and is_pattern_card(lemma):
            row['pos'] = 'grammatical pattern'
            pos_fixes += 1
    
    print(f"  Fixed {pos_fixes} POS labels")
    
    # Step 6: Re-rank everything by frequency
    print("\n📈 Step 6: Re-ranking all entries by frequency...")
    
    # Sort by frequency score (descending)
    rows_to_keep.sort(key=lambda x: float(x.get('Frequency_Score', '0')), reverse=True)
    
    # Assign new ranks
    for i, row in enumerate(rows_to_keep):
        row['Rank'] = str(i + 1)
    
    # Step 7: Trim to exactly 2000 entries
    print("\n✂️ Step 7: Trimming to 2000 entries...")
    if len(rows_to_keep) > 2000:
        rows_to_keep = rows_to_keep[:2000]
        print(f"  Trimmed to 2000 entries")
    else:
        print(f"  Current count: {len(rows_to_keep)} entries")
    
    # Step 8: Verify example sentences match
    print("\n🔍 Step 8: Flagging mismatched examples...")
    mismatched = []
    for row in rows_to_keep:
        lemma = row.get('original_word', row.get('lemma', ''))
        example = row.get('example_vi', '')
        
        # Clean lemma for matching
        clean_lemma = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)
        clean_lemma = re.sub(r'[VNS]\s*\+\s*|\s*\+\s*[VNS]|\[Clause\]\s*\+\s*|\s*\+\s*\[Clause\]', '', clean_lemma).strip()
        
        # Check if lemma appears in example
        if clean_lemma and clean_lemma.lower() not in example.lower():
            # For compounds, check if any part is in example
            parts = clean_lemma.split()
            if not any(part.lower() in example.lower() for part in parts if len(part) > 1):
                mismatched.append({
                    'rank': row.get('Rank'),
                    'lemma': lemma,
                    'example': example[:50]
                })
    
    print(f"  Found {len(mismatched)} entries with potentially mismatched examples")
    if mismatched[:5]:
        for m in mismatched[:5]:
            print(f"    Rank {m['rank']}: {m['lemma']} - \"{m['example']}...\"")
    
    # Save cleaned data
    print("\n💾 Saving cleaned data...")
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_keep)
    
    print(f"✓ Saved {len(rows_to_keep)} entries")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 Original entries: {len(rows)}")
    print(f"✂️ Trimmed over-expanded: {trimmed_count}")
    print(f"🔗 Consolidated patterns: {pattern_removed}")
    print(f"🏷️ Fixed POS labels: {pos_fixes}")
    print(f"📈 Final entries: {len(rows_to_keep)}")
    print(f"⚠️ Mismatched examples: {len(mismatched)}")
    
    if mismatched:
        print("\n⚠️ Next: Run fix_examples.py to fix mismatched example sentences")

if __name__ == "__main__":
    main()

