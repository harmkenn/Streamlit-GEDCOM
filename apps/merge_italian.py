"""
Book of Mormon - Merge English JSON with Italian Translation
This script takes your English JSON and adds Italian translations from the Church website.

Installation:
pip install requests beautifulsoup4

Usage:
python merge_italian.py
"""

import requests
import json
from bs4 import BeautifulSoup
import time
import os

# Book abbreviations for Church website URLs
BOOK_ABBREVIATIONS = {
    '1 Nephi': '1-ne',
    '2 Nephi': '2-ne',
    'Jacob': 'jacob',
    'Enos': 'enos',
    'Jarom': 'jarom',
    'Omni': 'omni',
    'Words of Mormon': 'w-of-m',
    'Mosiah': 'mosiah',
    'Alma': 'alma',
    'Helaman': 'hel',
    '3 Nephi': '3-ne',
    '4 Nephi': '4-ne',
    'Mormon': 'morm',
    'Ether': 'ether',
    'Moroni': 'moro'
}

def load_english_json(filepath='book-of-mormon.json'):
    """Load your English Book of Mormon JSON file"""
    print(f"Loading English JSON from {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        print("Please place your English JSON file in the same directory.")
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ Loaded English data")
    return data

def parse_english_json(data):
    """Convert English JSON to verse list format"""
    verses = []
    
    # Handle different possible JSON structures
    if isinstance(data, dict):
        if 'books' in data:
            # Format: {books: [...]}
            for book in data['books']:
                book_name = book.get('book', book.get('name', ''))
                for chapter in book.get('chapters', []):
                    chapter_num = chapter.get('chapter', chapter.get('number', 1))
                    for verse in chapter.get('verses', []):
                        verse_num = verse.get('verse', verse.get('number', 1))
                        text = verse.get('text', '')
                        verses.append({
                            'book': book_name,
                            'chapter': chapter_num,
                            'verse': verse_num,
                            'english': text,
                            'italian': ''
                        })
        elif 'chapters' in data:
            # Other possible formats
            pass
    elif isinstance(data, list):
        # Format: [{book, chapter, verse, text}, ...]
        for item in data:
            verses.append({
                'book': item.get('book', ''),
                'chapter': item.get('chapter', 1),
                'verse': item.get('verse', 1),
                'english': item.get('text', item.get('english', '')),
                'italian': ''
            })
    
    print(f"✓ Parsed {len(verses)} verses")
    return verses

def fetch_italian_chapter(book_name, chapter_num):
    """Fetch an entire chapter in Italian from Church website"""
    book_abbr = BOOK_ABBREVIATIONS.get(book_name)
    
    if not book_abbr:
        print(f"Warning: Unknown book '{book_name}'")
        return {}
    
    url = f"https://www.churchofjesuschrist.org/study/scriptures/bofm/{book_abbr}/{chapter_num}?lang=ita"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        verses = {}
        
        # Find all verse paragraphs
        verse_elements = soup.find_all('p', class_='verse')
        
        for elem in verse_elements:
            # Try to get verse number from marker
            verse_marker = elem.find('span', class_='verse-number')
            if verse_marker:
                verse_num_text = verse_marker.get_text(strip=True)
                try:
                    verse_num = int(verse_num_text)
                except:
                    continue
                
                # Get the text content
                text = elem.get_text(strip=True)
                # Remove verse number from beginning
                if text.startswith(verse_num_text):
                    text = text[len(verse_num_text):].strip()
                
                verses[verse_num] = text
        
        return verses
        
    except Exception as e:
        print(f"  Error fetching {book_name} {chapter_num}: {e}")
        return {}

def add_italian_translations(verses, save_progress_every=50):
    """Add Italian translations by fetching chapters from Church website"""
    print("\n" + "="*60)
    print("Fetching Italian translations from churchofjesuschrist.org")
    print("="*60)
    
    total = len(verses)
    current_book = None
    current_chapter = None
    chapter_verses = {}
    processed = 0
    
    try:
        for i, verse in enumerate(verses):
            # Check if we need to fetch a new chapter
            if verse['book'] != current_book or verse['chapter'] != current_chapter:
                current_book = verse['book']
                current_chapter = verse['chapter']
                
                print(f"\nFetching: {current_book} {current_chapter}")
                chapter_verses = fetch_italian_chapter(current_book, current_chapter)
                
                # Rate limiting - be nice to the server
                time.sleep(0.5)
                
                # Save progress periodically
                if i > 0 and i % save_progress_every == 0:
                    save_progress(verses, 'book_of_mormon_bilingual_progress.json')
                    print(f"  Progress saved: {i}/{total} verses ({i/total*100:.1f}%)")
            
            # Add Italian text if available
            if verse['verse'] in chapter_verses:
                verse['italian'] = chapter_verses[verse['verse']]
                processed += 1
            else:
                print(f"  Warning: Verse not found - {verse['book']} {verse['chapter']}:{verse['verse']}")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
        save_progress(verses, 'book_of_mormon_bilingual_interrupted.json')
        print("Progress saved to: book_of_mormon_bilingual_interrupted.json")
        return verses
    
    print(f"\n✓ Added Italian to {processed}/{total} verses")
    return verses

def save_progress(verses, filename):
    """Save progress to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

def main():
    print("="*60)
    print("Book of Mormon - English/Italian Merger")
    print("="*60)
    print()
    
    # Step 1: Load English JSON
    english_file = input("Enter English JSON filename (press Enter for 'book-of-mormon.json'): ").strip()
    if not english_file:
        english_file = 'book-of-mormon.json'
    
    data = load_english_json(english_file)
    if not data:
        return
    
    # Step 2: Parse to verse list
    verses = parse_english_json(data)
    
    if not verses:
        print("Error: Could not parse verses from JSON")
        print("Your JSON structure might be different. Can you show me a sample?")
        return
    
    print(f"\nFound {len(verses)} verses")
    print(f"First verse: {verses[0]['book']} {verses[0]['chapter']}:{verses[0]['verse']}")
    print(f"Text sample: {verses[0]['english'][:100]}...")
    print()
    
    # Step 3: Confirm and fetch Italian
    response = input("\nFetch Italian translations? (y/n): ").strip().lower()
    
    if response == 'y':
        verses = add_italian_translations(verses)
        
        # Save final result
        output_file = 'book_of_mormon_bilingual.json'
        save_progress(verses, output_file)
        print(f"\n✓ Saved to {output_file}")
        
        # Statistics
        with_italian = sum(1 for v in verses if v['italian'])
        print(f"\nStatistics:")
        print(f"  Total verses: {len(verses)}")
        print(f"  With Italian: {with_italian} ({with_italian/len(verses)*100:.1f}%)")
        print(f"  Missing: {len(verses) - with_italian}")
    else:
        print("\nCancelled. No Italian added.")

if __name__ == "__main__":
    main()