#!/usr/bin/env python3
"""
Filter rare polysemy senses from enriched_deck_data.csv.

This script:
1. Identifies polysemous entries (total_senses > 1)
2. Asks Gemini to estimate frequency of each sense
3. Removes senses marked as "rare" (<10% of usage)
4. Outputs filtered data

Then continues processing more candidates to reach 2000 entries.
"""

import csv
import json
import os
import time
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Target number of entries
TARGET_ENTRIES = 2000

# Batch size for Gemini API
BATCH_SIZE = 20

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2


def setup_gemini():
    """Configure the Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


def create_frequency_prompt(entries: List[Dict]) -> str:
    """Create a prompt to assess sense frequency."""
    
    sense_list = []
    for e in entries:
        sense_list.append(f'- "{e["lemma"]}": {e["pos"]} - {e["english_definition"]}')
    
    senses_text = "\n".join(sense_list)
    
    prompt = f"""You are a Vietnamese language expert. For each word sense below, estimate how frequently a Vietnamese learner would encounter this specific meaning in everyday speech, media, and text.

Word senses to evaluate:
{senses_text}

For EACH sense, respond with:
- "common" if this sense represents >30% of the word's usage (learners will see it often)
- "moderate" if 10-30% of usage (learners should know it)
- "rare" if <10% of usage (specialized, literary, or archaic - can be skipped for beginners)

Return a JSON array with your assessments:
[
  {{"lemma": "là₁", "frequency": "common", "reason": "primary meaning"}},
  {{"lemma": "là₃", "frequency": "rare", "reason": "literary/archaic usage"}}
]

Be strict - only mark as "common" or "moderate" if a learner would genuinely encounter this sense regularly. Many secondary senses are actually rare.

Return ONLY the JSON array."""

    return prompt


def parse_frequency_response(response_text: str) -> Dict[str, str]:
    """Parse Gemini's frequency assessment response."""
    try:
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        text = text.strip()
        
        # Find JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx + 1]
        
        data = json.loads(text)
        
        # Convert to dict: lemma -> frequency
        result = {}
        for item in data:
            lemma = item.get('lemma', '')
            freq = item.get('frequency', 'moderate').lower()
            result[lemma] = freq
        
        return result
        
    except Exception as e:
        print(f"  ⚠️  Parse error: {e}")
        return {}


def assess_sense_frequency(model, entries: List[Dict]) -> Dict[str, str]:
    """Get frequency assessment for a batch of entries."""
    
    for attempt in range(MAX_RETRIES):
        try:
            prompt = create_frequency_prompt(entries)
            response = model.generate_content(prompt)
            result = parse_frequency_response(response.text)
            
            if result:
                return result
                
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_BASE * (2 ** attempt))
            else:
                print(f"  ❌ Failed after {MAX_RETRIES} attempts: {e}")
    
    # Default to keeping all if assessment fails
    return {e['lemma']: 'moderate' for e in entries}


def filter_rare_senses(
    input_file: str = "enriched_deck_data.csv",
    output_file: str = "enriched_deck_data_filtered.csv"
):
    """Filter rare senses from enriched data."""
    
    print("="*60)
    print("Filtering Rare Polysemy Senses")
    print("="*60)
    
    # Setup
    model = setup_gemini()
    print("✓ Connected to Gemini 2.5 Flash")
    
    # Read current data
    print(f"\n📖 Reading {input_file}...")
    entries = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        entries = list(reader)
    
    print(f"  ✓ Loaded {len(entries)} entries")
    
    # Identify polysemous entries
    polysemy_entries = [e for e in entries if int(e.get('total_senses', 1)) > 1]
    single_entries = [e for e in entries if int(e.get('total_senses', 1)) == 1]
    
    print(f"  📊 Single-sense entries: {len(single_entries)} (keeping all)")
    print(f"  📊 Polysemy entries to evaluate: {len(polysemy_entries)}")
    
    # Assess frequency of polysemy entries in batches
    print(f"\n🔍 Assessing sense frequencies...")
    
    frequency_map = {}  # lemma -> frequency
    
    for i in range(0, len(polysemy_entries), BATCH_SIZE):
        batch = polysemy_entries[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(polysemy_entries) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"  Batch {batch_num}/{total_batches}...", end=" ")
        
        assessments = assess_sense_frequency(model, batch)
        frequency_map.update(assessments)
        
        # Count results
        common = sum(1 for v in assessments.values() if v == 'common')
        moderate = sum(1 for v in assessments.values() if v == 'moderate')
        rare = sum(1 for v in assessments.values() if v == 'rare')
        
        print(f"✓ common:{common} moderate:{moderate} rare:{rare}")
    
    # Filter out rare senses
    print(f"\n✂️  Filtering rare senses...")
    
    kept_entries = []
    removed_entries = []
    
    # Keep all single-sense entries
    kept_entries.extend(single_entries)
    
    # Filter polysemy entries
    for entry in polysemy_entries:
        lemma = entry['lemma']
        freq = frequency_map.get(lemma, 'moderate')
        
        if freq == 'rare':
            removed_entries.append(entry)
        else:
            entry['sense_frequency'] = freq  # Add frequency info
            kept_entries.append(entry)
    
    print(f"  ✓ Kept: {len(kept_entries)} entries")
    print(f"  ✗ Removed: {len(removed_entries)} rare senses")
    
    # Sort by original rank
    kept_entries.sort(key=lambda x: int(x.get('Rank', 9999)))
    
    # Re-assign ranks
    for i, entry in enumerate(kept_entries, 1):
        entry['Rank'] = i
    
    # Write filtered output
    print(f"\n💾 Writing to {output_file}...")
    
    fieldnames = list(kept_entries[0].keys()) if kept_entries else []
    if 'sense_frequency' not in fieldnames:
        fieldnames.append('sense_frequency')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(kept_entries)
    
    # Summary
    print("\n" + "="*60)
    print("✅ FILTERING COMPLETE")
    print("="*60)
    print(f"📊 Original entries: {len(entries)}")
    print(f"📊 After filtering: {len(kept_entries)}")
    print(f"📊 Removed (rare): {len(removed_entries)}")
    print(f"📊 Gap to fill: {TARGET_ENTRIES - len(kept_entries)}")
    
    # Show some removed examples
    if removed_entries:
        print(f"\n🗑️  Examples of removed rare senses:")
        for entry in removed_entries[:10]:
            print(f"   {entry['lemma']}: {entry.get('english_definition', 'N/A')}")
    
    return kept_entries, len(removed_entries)


if __name__ == "__main__":
    filter_rare_senses(
        input_file="enriched_deck_data.csv",
        output_file="enriched_deck_data_filtered.csv"
    )

