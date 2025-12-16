#!/usr/bin/env python3
"""
Clean the enriched deck data by removing proper nouns and verify frequency ranking.
"""

import csv
import re
from wordfreq import zipf_frequency

# Entries to remove (lemma values)
ENTRIES_TO_REMOVE = {
    'john',      # English given name
    'video',     # English loanword
    'nguyễn',    # Vietnamese surname
    'lê₃',       # surname sense
    'quân₂',     # given name sense
    'thiên₂',    # given name sense
}

def get_base_word(lemma: str) -> str:
    """Get the base word without sense subscripts."""
    return re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', lemma)

def clean_and_verify():
    print("=" * 60)
    print("Cleaning and Verifying Deck Data")
    print("=" * 60)
    
    # Read current data
    with open('enriched_deck_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"\n📖 Loaded {len(rows)} entries")
    
    # Remove proper nouns
    print(f"\n🗑️  Removing {len(ENTRIES_TO_REMOVE)} proper noun entries...")
    removed = []
    cleaned_rows = []
    
    for row in rows:
        lemma = row.get('lemma', '')
        if lemma in ENTRIES_TO_REMOVE:
            removed.append(f"  - {lemma} (rank {row.get('Rank', '?')})")
        else:
            cleaned_rows.append(row)
    
    for r in removed:
        print(r)
    
    print(f"\n✓ Removed {len(removed)} entries")
    print(f"✓ Remaining: {len(cleaned_rows)} entries")
    
    # Verify frequency ranking
    print(f"\n🔍 Verifying frequency ranking...")
    
    mismatches = []
    frequency_data = []
    
    for row in cleaned_rows:
        lemma = row.get('lemma', '')
        base_word = get_base_word(lemma)
        stored_freq = float(row.get('Frequency_Score', 0))
        
        # Look up fresh frequency
        fresh_freq = zipf_frequency(base_word, 'vi')
        
        frequency_data.append({
            'lemma': lemma,
            'base_word': base_word,
            'stored_freq': stored_freq,
            'fresh_freq': fresh_freq,
            'diff': abs(stored_freq - fresh_freq),
            'row': row
        })
        
        # Flag significant mismatches (>0.5 difference)
        if abs(stored_freq - fresh_freq) > 0.5:
            mismatches.append({
                'lemma': lemma,
                'rank': row.get('Rank', '?'),
                'stored': stored_freq,
                'fresh': fresh_freq,
                'diff': stored_freq - fresh_freq
            })
    
    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} frequency mismatches (diff > 0.5):")
        for m in mismatches[:10]:  # Show first 10
            print(f"  - {m['lemma']} (rank {m['rank']}): stored={m['stored']:.2f}, fresh={m['fresh']:.2f}, diff={m['diff']:+.2f}")
        if len(mismatches) > 10:
            print(f"  ... and {len(mismatches) - 10} more")
    else:
        print("✓ All frequency scores match!")
    
    # Check if current ranking is correct (sorted by frequency)
    print(f"\n🔢 Checking if entries are sorted by frequency...")
    
    # Sort by fresh frequency (descending)
    sorted_data = sorted(frequency_data, key=lambda x: x['fresh_freq'], reverse=True)
    
    # Compare ranks
    rank_changes = []
    for i, item in enumerate(sorted_data):
        current_rank = int(item['row'].get('Rank', 0))
        new_rank = i + 1
        if abs(current_rank - new_rank) > 10:  # Flag if rank changes by more than 10
            rank_changes.append({
                'lemma': item['lemma'],
                'current_rank': current_rank,
                'should_be_rank': new_rank,
                'freq': item['fresh_freq']
            })
    
    if rank_changes:
        print(f"\n⚠️  Found {len(rank_changes)} entries with significant rank changes:")
        for rc in rank_changes[:15]:
            print(f"  - {rc['lemma']}: rank {rc['current_rank']} → should be ~{rc['should_be_rank']} (freq={rc['freq']:.2f})")
        if len(rank_changes) > 15:
            print(f"  ... and {len(rank_changes) - 15} more")
    else:
        print("✓ Ranking looks correct!")
    
    # Write cleaned data (keeping original ranking for now)
    print(f"\n💾 Writing cleaned data...")
    
    with open('enriched_deck_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
    
    print(f"✓ Saved {len(cleaned_rows)} entries to enriched_deck_data.csv")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"📊 Original entries: {len(rows)}")
    print(f"🗑️  Removed: {len(removed)}")
    print(f"✅ Final count: {len(cleaned_rows)}")
    print(f"⚠️  Frequency mismatches: {len(mismatches)}")
    print(f"🔢 Rank changes needed: {len(rank_changes)}")

if __name__ == "__main__":
    clean_and_verify()

