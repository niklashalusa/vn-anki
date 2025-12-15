#!/usr/bin/env python3
"""
Enrich Vietnamese word data using Google's Gemini AI.

This script reads the raw lemmas from CSV and uses Gemini to generate:
- Part of Speech (POS)
- English Definition
- Example sentence in Vietnamese (Northern register)
- Example sentence in English

The data is processed in batches for efficiency.
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


def setup_gemini():
    """Configure the Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables.\n"
            "Please create a .env file with your API key:\n"
            "GEMINI_API_KEY=your_api_key_here\n"
            "Get your API key from: https://aistudio.google.com/app/apikey"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


def create_batch_prompt(words: List[Dict]) -> str:
    """
    Create a prompt for a batch of words.
    
    Args:
        words: List of word dictionaries with 'Rank', 'Lemma', 'Frequency_Score'
        
    Returns:
        Formatted prompt string
    """
    word_list = ", ".join([f'"{w["Lemma"]}"' for w in words])
    
    prompt = f"""You are a Vietnamese language expert. For each of the following Vietnamese words, provide detailed linguistic information.

Words to process: {word_list}

For each word, return a JSON object with the following fields:
1. "lemma": the original word
2. "pos": Part of Speech (noun, verb, adjective, adverb, particle, pronoun, conjunction, preposition, etc.)
3. "english_definition": A concise English definition (3-5 words maximum)
4. "example_vi": A natural example sentence in spoken Northern Vietnamese register (casual, everyday language)
5. "example_en": English translation of the example sentence

IMPORTANT CONSTRAINTS:
- For particles like "thì", "mà", "đã", "được", etc., set pos to "particle" and explain their grammatical function briefly in the definition
- Keep definitions SHORT and PRACTICAL (3-5 words)
- Example sentences should sound NATURAL and COLLOQUIAL (Northern Vietnamese)
- Example sentences should be SHORT (5-10 words)
- Use the word in context that shows its meaning clearly

Return ONLY a valid JSON array of objects, one for each word, in the same order as given. No additional text.

Example format:
[
  {{
    "lemma": "là",
    "pos": "verb",
    "english_definition": "to be",
    "example_vi": "Đây là nhà tôi.",
    "example_en": "This is my house."
  }},
  {{
    "lemma": "thì",
    "pos": "particle",
    "english_definition": "emphasizes contrast/condition",
    "example_vi": "Tôi thì thích ăn phở.",
    "example_en": "As for me, I like eating pho."
  }}
]"""
    
    return prompt


def parse_gemini_response(response_text: str) -> List[Dict]:
    """
    Parse Gemini's JSON response.
    
    Args:
        response_text: Raw response text from Gemini
        
    Returns:
        List of word data dictionaries
    """
    try:
        # Clean up the response - remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith('```'):
            # Remove ```json or ``` from start
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        text = text.strip()
        
        # Parse JSON
        data = json.loads(text)
        return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response text: {response_text[:500]}...")
        return []


def process_batch(model, words: List[Dict], batch_num: int, total_batches: int) -> List[Dict]:
    """
    Process a batch of words through Gemini.
    
    Args:
        model: Gemini model instance
        words: List of word dictionaries
        batch_num: Current batch number (for progress display)
        total_batches: Total number of batches
        
    Returns:
        List of enriched word data
    """
    print(f"Processing batch {batch_num}/{total_batches} ({len(words)} words)...")
    
    prompt = create_batch_prompt(words)
    
    try:
        response = model.generate_content(prompt)
        enriched_data = parse_gemini_response(response.text)
        
        if len(enriched_data) != len(words):
            print(f"⚠️  Warning: Expected {len(words)} results, got {len(enriched_data)}")
        
        # Merge with original data
        for original, enriched in zip(words, enriched_data):
            enriched['Rank'] = original['Rank']
            enriched['Frequency_Score'] = original['Frequency_Score']
        
        return enriched_data
        
    except Exception as e:
        print(f"❌ Error processing batch {batch_num}: {e}")
        # Return empty results with just the original data
        return [{
            'Rank': w['Rank'],
            'lemma': w['Lemma'],
            'Frequency_Score': w['Frequency_Score'],
            'pos': 'unknown',
            'english_definition': 'error',
            'example_vi': '',
            'example_en': ''
        } for w in words]


def enrich_vietnamese_words(
    input_file: str = "raw_lemmas.csv",
    output_file: str = "enriched_deck_data.csv",
    batch_size: int = 20
):
    """
    Main function to enrich Vietnamese word data.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        batch_size: Number of words to process per API call
    """
    # Setup
    print("Setting up Gemini API...")
    model = setup_gemini()
    
    # Read input data
    print(f"Reading {input_file}...")
    words = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        words = list(reader)
    
    print(f"Loaded {len(words)} words")
    
    # Process in batches
    all_enriched_data = []
    total_batches = (len(words) + batch_size - 1) // batch_size
    
    for i in range(0, len(words), batch_size):
        batch = words[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        enriched_batch = process_batch(model, batch, batch_num, total_batches)
        all_enriched_data.extend(enriched_batch)
        
        # Rate limiting - not needed with paid API
        if batch_num < total_batches:
            time.sleep(0)
    
    # Write output
    print(f"\nWriting {len(all_enriched_data)} enriched words to {output_file}...")
    
    fieldnames = [
        'Rank',
        'lemma',
        'Frequency_Score',
        'pos',
        'english_definition',
        'example_vi',
        'example_en'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_enriched_data)
    
    print(f"✓ Successfully created {output_file}")
    print(f"✓ Total enriched words: {len(all_enriched_data)}")
    
    # Show sample
    print(f"\nSample of first 3 enriched words:")
    for word in all_enriched_data[:3]:
        print(f"\n  {word['Rank']}. {word['lemma']} ({word['pos']})")
        print(f"     Definition: {word['english_definition']}")
        print(f"     Example: {word['example_vi']}")
        print(f"     Translation: {word['example_en']}")


if __name__ == "__main__":
    enrich_vietnamese_words(
        input_file="raw_lemmas.csv",
        output_file="enriched_deck_data.csv",
        batch_size=20
    )

