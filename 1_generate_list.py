#!/usr/bin/env python3
"""
Generate a comprehensive list of Vietnamese vocabulary candidates.

This script combines:
1. Single words from wordfreq frequency list
2. Common compound words scored by wordfreq

Output: candidate_words.csv ranked by frequency
"""

import csv
import os
import json
from wordfreq import top_n_list, zipf_frequency
from underthesea import word_tokenize
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Common Vietnamese compound words by category
# These will be scored by wordfreq and merged with single words
COMPOUND_CATEGORIES = {
    'Food & Drink': [
        'thức ăn', 'đồ ăn', 'cơm chiên', 'bánh mì', 'nước uống', 'đồ uống',
        'bữa sáng', 'bữa trưa', 'bữa tối', 'đồ ngọt', 'trái cây', 'rau củ',
        'thịt bò', 'thịt gà', 'thịt lợn', 'cá biển', 'hải sản', 'món ăn',
    ],
    'Transport': [
        'xe máy', 'xe đạp', 'xe hơi', 'xe ô tô', 'máy bay', 'xe buýt', 
        'tàu hỏa', 'tàu điện', 'xe taxi', 'xe khách', 'phương tiện',
    ],
    'Places': [
        'bệnh viện', 'trường học', 'nhà hàng', 'khách sạn', 'siêu thị', 
        'sân bay', 'nhà ga', 'bưu điện', 'ngân hàng', 'công viên',
        'thư viện', 'bảo tàng', 'nhà thờ', 'chùa chiền', 'cửa hàng',
        'chợ búa', 'quán cà phê', 'tiệm thuốc', 'phòng khám',
    ],
    'People & Occupations': [
        'giáo viên', 'học sinh', 'sinh viên', 'bác sĩ', 'công nhân', 
        'nhân viên', 'kỹ sư', 'luật sư', 'ca sĩ', 'diễn viên',
        'nông dân', 'thợ may', 'thợ điện', 'thợ mộc', 'lái xe',
        'bạn bè', 'người yêu', 'vợ chồng', 'con cái', 'cha mẹ',
        'ông bà', 'anh chị', 'em bé', 'trẻ em', 'người lớn',
    ],
    'Work & Life': [
        'công việc', 'cuộc sống', 'gia đình', 'tình yêu', 'sức khỏe',
        'tiền bạc', 'thời gian', 'cuộc đời', 'tương lai', 'quá khứ',
        'hiện tại', 'thành công', 'thất bại', 'hạnh phúc', 'buồn bã',
    ],
    'Technology': [
        'điện thoại', 'máy tính', 'internet', 'website', 'email',
        'mạng xã hội', 'tin nhắn', 'video call', 'máy ảnh', 'tivi',
    ],
    'Time Expressions': [
        'hôm nay', 'hôm qua', 'ngày mai', 'tuần này', 'năm nay',
        'tháng này', 'sáng nay', 'tối nay', 'đêm qua', 'mỗi ngày',
        'hàng tuần', 'hàng tháng', 'hàng năm', 'lâu rồi', 'gần đây',
    ],
    'Common Expressions': [
        'như vậy', 'tuy nhiên', 'ngoài ra', 'vì vậy', 'do đó',
        'mặc dù', 'dù sao', 'có lẽ', 'chắc chắn', 'tất nhiên',
        'thực ra', 'thật sự', 'có thể', 'không thể', 'cần phải',
    ],
    'Nature & Weather': [
        'thời tiết', 'mặt trời', 'mặt trăng', 'bầu trời', 'biển cả',
        'núi non', 'sông ngòi', 'rừng rậm', 'đồng bằng', 'sa mạc',
    ],
    'Body & Health': [
        'cơ thể', 'đầu óc', 'trái tim', 'bàn tay', 'bàn chân',
        'mắt mũi', 'tai miệng', 'sức khỏe', 'bệnh tật', 'thuốc men',
    ],
    'Education': [
        'bài học', 'bài tập', 'bài kiểm tra', 'kỳ thi', 'điểm số',
        'lớp học', 'môn học', 'sách vở', 'giáo dục', 'kiến thức',
    ],
    'Numbers & Measurements': [
        'số lượng', 'kích thước', 'trọng lượng', 'khoảng cách', 'tốc độ',
    ],
}


def setup_gemini():
    """Configure the Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⚠️  GEMINI_API_KEY not found - using only predefined compounds")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


def get_additional_compounds_from_gemini(model, existing_compounds):
    """Ask Gemini to suggest additional important Vietnamese compounds."""
    if not model:
        return []
    
    print("\n🤖 Asking Gemini for additional compound suggestions...")
    
    prompt = f"""You are a Vietnamese language expert. I need to identify the most important Vietnamese compound words (từ ghép) that a learner should know.

I already have these compounds: {', '.join(list(existing_compounds)[:50])}...

Please suggest 100 MORE essential Vietnamese compound words that are:
1. Commonly used in everyday speech
2. Not easily understood from individual components
3. Important for a language learner to know as a unit

Focus on categories like:
- Everyday objects and concepts
- Abstract concepts
- Common verbs/verb phrases that function as compounds
- Idiomatic expressions that are single concepts

Return ONLY a JSON array of strings, no explanation:
["compound1", "compound2", ...]"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up response
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        text = text.strip()
        
        compounds = json.loads(text)
        print(f"  ✓ Gemini suggested {len(compounds)} additional compounds")
        return compounds
    except Exception as e:
        print(f"  ⚠️  Gemini request failed: {e}")
        return []


def is_valid_entry(word):
    """Check if a word/compound is valid for the deck."""
    # Must have at least one Vietnamese character
    if not any('\u00C0' <= c <= '\u1EF9' or c.isalpha() for c in word):
        return False
    
    # Skip pure numbers
    if word.replace(' ', '').isdigit():
        return False
    
    # Skip single characters
    if len(word.strip()) < 2:
        return False
    
    # Skip entries that are just punctuation
    if all(c in '.,;:!?-_()[]{}' for c in word.replace(' ', '')):
        return False
    
    return True


def generate_candidate_list(output_file="candidate_words.csv"):
    """
    Generate a comprehensive list of Vietnamese vocabulary candidates.
    
    Combines single words from wordfreq with compound words, all scored by frequency.
    """
    print("="*60)
    print("Generating Vietnamese Vocabulary Candidates")
    print("="*60)
    
    # Setup Gemini
    model = setup_gemini()
    
    # Step 1: Get single words from wordfreq
    print("\n📖 Step 1: Getting single words from wordfreq...")
    single_words = top_n_list('vi', 2500)  # Get extra to allow for filtering
    print(f"  Retrieved {len(single_words)} single words")
    
    # Step 2: Collect compound words
    print("\n📖 Step 2: Collecting compound words...")
    compounds = set()
    for category, words in COMPOUND_CATEGORIES.items():
        for word in words:
            compounds.add(word)
    print(f"  Predefined compounds: {len(compounds)}")
    
    # Get additional compounds from Gemini
    additional = get_additional_compounds_from_gemini(model, compounds)
    for word in additional:
        if isinstance(word, str) and len(word) > 1:
            compounds.add(word.strip())
    print(f"  Total compounds after Gemini: {len(compounds)}")
    
    # Step 3: Score all entries and merge
    print("\n📊 Step 3: Scoring and ranking all entries...")
    
    all_entries = []
    seen_words = set()
    
    # Add single words with scores
    for word in single_words:
        if word in seen_words:
            continue
        if not is_valid_entry(word):
            continue
        
        freq = zipf_frequency(word, 'vi')
        if freq > 0:
            tokens = word_tokenize(word)
            all_entries.append({
                'Word': word,
                'Is_Compound': len(tokens) > 1,
                'Token_Count': len(tokens),
                'Frequency_Score': round(freq, 4)
            })
            seen_words.add(word)
    
    print(f"  Valid single words: {len(all_entries)}")
    
    # Add compound words with scores
    compounds_added = 0
    compounds_scored = 0
    for word in compounds:
        if word in seen_words:
            continue
        if not is_valid_entry(word):
            continue
        
        freq = zipf_frequency(word, 'vi')
        if freq > 0:
            compounds_scored += 1
            tokens = word_tokenize(word)
            all_entries.append({
                'Word': word,
                'Is_Compound': True,
                'Token_Count': len(tokens),
                'Frequency_Score': round(freq, 4)
            })
            seen_words.add(word)
            compounds_added += 1
    
    print(f"  Compounds with frequency scores: {compounds_added}")
    print(f"  Total candidates: {len(all_entries)}")
    
    # Step 4: Sort by frequency and rank
    print("\n🔢 Step 4: Sorting by frequency...")
    all_entries.sort(key=lambda x: x['Frequency_Score'], reverse=True)
    
    # Add ranks
    for i, entry in enumerate(all_entries, 1):
        entry['Rank'] = i
    
    # Step 5: Write to CSV
    print(f"\n💾 Step 5: Writing to {output_file}...")
    
    fieldnames = ['Rank', 'Word', 'Is_Compound', 'Token_Count', 'Frequency_Score']
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_entries)
    
    # Summary
    print("\n" + "="*60)
    print("✅ CANDIDATE LIST GENERATED")
    print("="*60)
    print(f"📦 Output file: {output_file}")
    print(f"📊 Total candidates: {len(all_entries)}")
    
    # Breakdown
    single_count = sum(1 for e in all_entries if not e['Is_Compound'])
    compound_count = sum(1 for e in all_entries if e['Is_Compound'])
    print(f"\n📈 Breakdown:")
    print(f"   Single words: {single_count}")
    print(f"   Compounds: {compound_count}")
    
    # Show frequency distribution
    freq_cutoffs = [7.0, 6.5, 6.0, 5.5, 5.0, 4.5]
    print(f"\n📊 Frequency distribution:")
    for cutoff in freq_cutoffs:
        count = sum(1 for e in all_entries if e['Frequency_Score'] >= cutoff)
        print(f"   ≥{cutoff}: {count} entries")
    
    # Show top entries
    print(f"\n🔝 Top 15 entries:")
    for entry in all_entries[:15]:
        compound_marker = "📦" if entry['Is_Compound'] else "  "
        print(f"   {compound_marker} #{entry['Rank']:4d} {entry['Word']:15s} (freq: {entry['Frequency_Score']:.2f})")
    
    # Show compound examples in top 500
    print(f"\n📦 Compounds in top 500:")
    compound_examples = [e for e in all_entries[:500] if e['Is_Compound']]
    for entry in compound_examples[:15]:
        print(f"   #{entry['Rank']:4d} {entry['Word']:15s} (freq: {entry['Frequency_Score']:.2f})")
    
    return all_entries


if __name__ == "__main__":
    generate_candidate_list(output_file="candidate_words.csv")
