#!/usr/bin/env python3
"""
Generate a list of the top 2000 most frequent Vietnamese words.

This script uses the wordfreq library to get the most common Vietnamese words,
validates them using underthesea word tokenization, and saves the results to CSV.
"""

import csv
from wordfreq import top_n_list, zipf_frequency
from underthesea import word_tokenize


def is_valid_lemma(word):
    """
    Validate that a word is a single lemma and not a sentence fragment.
    
    Uses underthesea word tokenization to check if the word is a single token.
    
    Args:
        word: The word to validate
        
    Returns:
        bool: True if the word is a valid single lemma, False otherwise
    """
    try:
        tokens = word_tokenize(word)
        # Valid lemma should tokenize to itself (single token)
        # or the tokens should match the original word when joined
        if len(tokens) == 1:
            return True
        # Some words might have spaces but still be single concepts
        # Filter out obvious sentence fragments (multiple meaningful tokens)
        return len(tokens) <= 2 and len(word.split()) <= 1
    except Exception as e:
        print(f"Error tokenizing '{word}': {e}")
        return False


def generate_vietnamese_word_list(n=2000, output_file="raw_lemmas.csv"):
    """
    Generate a list of top N most frequent Vietnamese words.
    
    Args:
        n: Number of top words to retrieve (default: 2000)
        output_file: Output CSV filename (default: raw_lemmas.csv)
    """
    print(f"Fetching top {n} Vietnamese words from wordfreq...")
    
    # Get top N Vietnamese words
    top_words = top_n_list('vi', n)
    
    print(f"Retrieved {len(top_words)} words. Validating...")
    
    # Prepare data for CSV
    word_data = []
    rank = 1
    
    for word in top_words:
        # Validate the word
        if is_valid_lemma(word):
            # Get frequency score
            freq_score = zipf_frequency(word, 'vi')
            
            word_data.append({
                'Rank': rank,
                'Lemma': word,
                'Frequency_Score': round(freq_score, 4)
            })
            rank += 1
        else:
            print(f"Filtered out: '{word}' (not a valid lemma)")
    
    # Write to CSV
    print(f"\nWriting {len(word_data)} validated words to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Rank', 'Lemma', 'Frequency_Score']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(word_data)
    
    print(f"✓ Successfully generated {output_file}")
    print(f"✓ Total validated words: {len(word_data)}")
    print(f"\nSample of top 10 words:")
    for i, word in enumerate(word_data[:10], 1):
        print(f"  {i}. {word['Lemma']} (score: {word['Frequency_Score']})")


if __name__ == "__main__":
    generate_vietnamese_word_list(n=2000, output_file="raw_lemmas.csv")

