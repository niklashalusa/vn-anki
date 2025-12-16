#!/usr/bin/env python3
"""
Enrich Vietnamese vocabulary with definitions and polysemy expansion.

This script:
1. Reads candidate words from candidate_words.csv
2. Uses Gemini to identify polysemous words and expand them
3. Generates definitions and example sentences
4. Stops at exactly 2000 entries

Output: enriched_deck_data.csv with exactly 2000 rows
"""

import csv
import json
import os
import time
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Target number of entries
TARGET_ENTRIES = 2000

# Batch size for Gemini API
BATCH_SIZE = 15

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds


def setup_gemini():
    """Configure the Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables.\n"
            "Please create a .env file with your API key."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


def create_enrichment_prompt(words: List[Dict]) -> str:
    """
    Create a prompt for enriching words with polysemy detection.
    """
    word_list = ", ".join([f'"{w["Word"]}"' for w in words])
    
    prompt = f"""You are a Vietnamese language expert helping create an Anki deck.

For each word below, determine if it has MULTIPLE DISTINCT senses that a learner needs as separate cards.

Words to process: {word_list}

For EACH word, analyze:
1. Does this word have multiple clearly different meanings?
2. If yes, create SEPARATE entries for each distinct sense

Return a JSON array where each word may produce 1 OR MORE entries:

[
  {{
    "original_word": "để",
    "lemma": "để₁",
    "sense_number": 1,
    "total_senses": 3,
    "pos": "particle",
    "english_definition": "in order to, so that",
    "example_vi": "Tôi học để thi.",
    "example_en": "I study in order to take the exam."
  }},
  {{
    "original_word": "để",
    "lemma": "để₂",
    "sense_number": 2,
    "total_senses": 3,
    "pos": "verb",
    "english_definition": "to put, to place, to leave",
    "example_vi": "Để sách ở đây.",
    "example_en": "Put the book here."
  }},
  {{
    "original_word": "nhà",
    "lemma": "nhà",
    "sense_number": 1,
    "total_senses": 1,
    "pos": "noun",
    "english_definition": "house, home",
    "example_vi": "Nhà tôi ở gần đây.",
    "example_en": "My house is nearby."
  }}
]

RULES:
1. Only split if meanings are CLEARLY DISTINCT (not just nuanced)
2. Function words (được, cho, mà, thì, là) often need splitting
3. Common verbs with metaphorical uses may need splitting
4. Most nouns need only 1 entry
5. Keep definitions SHORT (3-5 words)
6. Example sentences should be natural, spoken Northern Vietnamese (5-10 words)
7. Use subscript notation for multiple senses (để₁, để₂)

Return ONLY valid JSON array. No explanation."""

    return prompt


def parse_enrichment_response(response_text: str) -> List[Dict]:
    """Parse Gemini's JSON response with robust error handling."""
    try:
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        text = text.strip()
        
        # Try to find JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx + 1]
        
        data = json.loads(text)
        return data
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        
        # Try to extract partial data
        try:
            # Find individual objects and parse them
            entries = []
            import re
            objects = re.findall(r'\{[^{}]+\}', response_text)
            for obj_str in objects:
                try:
                    obj = json.loads(obj_str)
                    if 'lemma' in obj and 'english_definition' in obj:
                        entries.append(obj)
                except:
                    continue
            if entries:
                print(f"  ⚠️  Recovered {len(entries)} entries from malformed JSON")
                return entries
        except:
            pass
        
        return []


def process_batch_with_retry(model, words: List[Dict], batch_num: int, total_batches: int) -> List[Dict]:
    """Process a batch with retry logic."""
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Batch {batch_num}/{total_batches} ({len(words)} words)...", end=" ")
            
            prompt = create_enrichment_prompt(words)
            response = model.generate_content(prompt)
            entries = parse_enrichment_response(response.text)
            
            if entries:
                # Verify we got entries for all input words
                input_words = set(w['Word'] for w in words)
                output_words = set(e.get('original_word', e.get('lemma', '').rstrip('₁₂₃₄₅₆₇₈₉₀')) for e in entries)
                
                missing = input_words - output_words
                if missing:
                    print(f"⚠️  Missing: {missing}")
                else:
                    print(f"✓ {len(entries)} entries")
                
                return entries
            else:
                print(f"⚠️  Empty response")
                
        except Exception as e:
            error_msg = str(e)
            if '504' in error_msg or 'Deadline' in error_msg:
                print(f"⚠️  Timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            elif '429' in error_msg or 'quota' in error_msg.lower():
                print(f"⚠️  Rate limit (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY_BASE * (attempt + 2))  # Longer wait for rate limit
            else:
                print(f"❌ Error: {error_msg[:50]}")
            
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                time.sleep(delay)
    
    # All retries failed - return fallback entries
    print(f"  ❌ All retries failed, using fallback")
    return [{
        'original_word': w['Word'],
        'lemma': w['Word'],
        'sense_number': 1,
        'total_senses': 1,
        'pos': 'unknown',
        'english_definition': '[needs review]',
        'example_vi': '',
        'example_en': '',
        'needs_review': True
    } for w in words]


def enrich_vocabulary(
    input_file: str = "candidate_words.csv",
    output_file: str = "enriched_deck_data.csv",
    target_entries: int = TARGET_ENTRIES
):
    """
    Enrich vocabulary with polysemy expansion.
    
    Processes candidates in frequency order, expanding polysemous words,
    and stops when reaching the target number of entries.
    """
    print("="*60)
    print("Enriching Vietnamese Vocabulary with Polysemy Expansion")
    print("="*60)
    
    # Setup
    print("\n🔧 Setting up Gemini API...")
    model = setup_gemini()
    print("  ✓ Connected to Gemini 2.5 Flash")
    
    # Read candidates
    print(f"\n📖 Reading candidates from {input_file}...")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    candidates = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)
    
    print(f"  ✓ Loaded {len(candidates)} candidates")
    
    # Process in batches
    print(f"\n🔄 Processing with target of {target_entries} entries...")
    print(f"  Batch size: {BATCH_SIZE}")
    
    all_entries = []
    processed_words = 0
    batch_num = 0
    
    # Process until we have enough entries
    while len(all_entries) < target_entries and processed_words < len(candidates):
        # Get next batch
        batch_start = processed_words
        batch_end = min(processed_words + BATCH_SIZE, len(candidates))
        batch = candidates[batch_start:batch_end]
        
        batch_num += 1
        total_batches = (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Process batch
        entries = process_batch_with_retry(model, batch, batch_num, total_batches)
        
        # Add entries with metadata
        for entry in entries:
            # Find original word data
            original_word = entry.get('original_word', entry.get('lemma', ''))
            original_data = next((c for c in batch if c['Word'] == original_word), None)
            
            if original_data:
                entry['Frequency_Score'] = original_data.get('Frequency_Score', 0)
                entry['Is_Compound'] = original_data.get('Is_Compound', False)
            
            all_entries.append(entry)
            
            # Check if we've reached target
            if len(all_entries) >= target_entries:
                print(f"\n🎯 Reached target of {target_entries} entries!")
                break
        
        processed_words = batch_end
        
        # Progress update
        if batch_num % 10 == 0:
            print(f"  📊 Progress: {len(all_entries)} entries from {processed_words} words")
    
    # Trim to exact target if we overshot
    if len(all_entries) > target_entries:
        print(f"  ✂️  Trimming from {len(all_entries)} to {target_entries} entries")
        all_entries = all_entries[:target_entries]
    
    # Add ranks
    for i, entry in enumerate(all_entries, 1):
        entry['Rank'] = i
    
    # Write output
    print(f"\n💾 Writing {len(all_entries)} entries to {output_file}...")
    
    fieldnames = [
        'Rank', 'lemma', 'original_word', 'sense_number', 'total_senses',
        'pos', 'english_definition', 'example_vi', 'example_en',
        'Frequency_Score', 'Is_Compound'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_entries)
    
    # Summary
    print("\n" + "="*60)
    print("✅ ENRICHMENT COMPLETE")
    print("="*60)
    print(f"📦 Output file: {output_file}")
    print(f"📊 Total entries: {len(all_entries)}")
    
    # Statistics
    needs_review = sum(1 for e in all_entries if e.get('needs_review'))
    polysemy_entries = sum(1 for e in all_entries if e.get('total_senses', 1) > 1)
    unique_words = len(set(e.get('original_word', e.get('lemma')) for e in all_entries))
    
    print(f"\n📈 Statistics:")
    print(f"   Unique words processed: {unique_words}")
    print(f"   Polysemy expansions: {polysemy_entries} entries from polysemous words")
    print(f"   Expansion ratio: {len(all_entries)/unique_words:.2f}x")
    if needs_review > 0:
        print(f"   ⚠️  Needs review: {needs_review} entries")
    
    # Show sample
    print(f"\n📝 Sample entries:")
    for entry in all_entries[:5]:
        sense_info = f" (sense {entry.get('sense_number')}/{entry.get('total_senses')})" if entry.get('total_senses', 1) > 1 else ""
        print(f"   {entry['Rank']}. {entry['lemma']}{sense_info}")
        print(f"      {entry.get('pos', 'unknown')}: {entry.get('english_definition', 'N/A')}")
        print(f"      Ex: {entry.get('example_vi', 'N/A')}")
    
    # Show polysemy examples
    polysemy_examples = [e for e in all_entries if e.get('total_senses', 1) > 1]
    if polysemy_examples:
        print(f"\n🔀 Polysemy examples:")
        seen_words = set()
        for entry in polysemy_examples[:10]:
            orig = entry.get('original_word', '')
            if orig not in seen_words:
                related = [e for e in all_entries if e.get('original_word') == orig]
                print(f"   {orig} → {len(related)} senses:")
                for r in related:
                    print(f"      {r['lemma']}: {r.get('english_definition', 'N/A')}")
                seen_words.add(orig)
                if len(seen_words) >= 3:
                    break
    
    return all_entries


if __name__ == "__main__":
    enrich_vocabulary(
        input_file="candidate_words.csv",
        output_file="enriched_deck_data.csv",
        target_entries=TARGET_ENTRIES
    )
