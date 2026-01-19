import streamlit as st
from datetime import datetime, date
import json
import os

# Page config
st.set_page_config(
    page_title="Book of Mormon Daily Reader",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
TOTAL_VERSES = 6604
VERSES_PER_DAY = int(TOTAL_VERSES / 365) + 1

# Sample data
SAMPLE_VERSES = [
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 1,
        "english": "I, Nephi, having been born of goodly parents, therefore I was taught somewhat in all the learning of my father; and having seen many afflictions in the course of my days, nevertheless, having been highly favored of the Lord in all my days; yea, having had a great knowledge of the goodness and the mysteries of God, therefore I make a record of my proceedings in my days."
    },
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 2,
        "english": "Yea, I make a record in the language of my father, which consists of the learning of the Jews and the language of the Egyptians."
    }
]

@st.cache_data
def load_verses():
    """Load Book of Mormon verses from JSON file and flatten into a list"""
    if os.path.exists('book_of_mormon.json'):
        try:
            with open('book_of_mormon.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Flatten the nested structure into a single list of verses
                verses_list = []
                
                if isinstance(data, dict) and 'books' in data:
                    for book_data in data['books']:
                        book_name = book_data.get('book', 'Unknown')
                        for chapter_data in book_data.get('chapters', []):
                            chapter_num = chapter_data.get('chapter', 0)
                            for verse_data in chapter_data.get('verses', []):
                                verse_entry = {
                                    'book': book_name,
                                    'chapter': chapter_num,
                                    'verse': verse_data.get('verse', 0),
                                    'english': verse_data.get('text', '')
                                }
                                verses_list.append(verse_entry)
                
                return verses_list if verses_list else SAMPLE_VERSES
        except Exception as e:
            st.error(f"Error loading verses: {e}")
            return SAMPLE_VERSES
    return SAMPLE_VERSES

def get_day_of_year(input_date):
    """Calculate day of year from a date"""
    start_of_year = date(input_date.year, 1, 1)
    return (input_date - start_of_year).days + 1

def get_verses_for_day(day_num, all_verses):
    """Get verses for a specific day"""
    start_idx = (day_num - 1) * VERSES_PER_DAY
    end_idx = min(start_idx + VERSES_PER_DAY, len(all_verses))
    return all_verses[start_idx:end_idx] if start_idx < len(all_verses) else all_verses[:VERSES_PER_DAY]

@st.cache_data
def translate_to_italian(text):
    """Translate English text to Italian using deep-translator"""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='en', target='it')
        translation = translator.translate(text)
        return translation
    except ImportError:
        return "[Translation unavailable - install deep-translator: pip install deep-translator]"
    except Exception as e:
        return f"[Translation error: {str(e)}]"

def split_into_phrases(text):
    """Split text into phrases based on natural breaks"""
    import re
    
    # Remove trailing period
    text = text.rstrip('.')
    
    # Split on semicolons first (these are major breaks)
    semicolon_parts = text.split(';')
    
    phrases = []
    for part in semicolon_parts:
        # Now split each part on commas
        comma_parts = [p.strip() for p in part.split(',') if p.strip()]
        phrases.extend(comma_parts)
    
    return phrases if phrases else [text]

@st.cache_data
def text_to_speech(text, lang='it'):
    """Convert text to speech using gTTS and return audio bytes"""
    try:
        from gtts import gTTS
        from io import BytesIO
        
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes.read()
    except ImportError:
        return None
    except Exception as e:
        st.error(f"TTS error: {str(e)}")
        return None

# Mobile-optimized CSS - System theme
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    .verse-text {
        font-size: 0.95em;
        line-height: 1.6;
    }
    
    hr {
        margin: 1rem 0;
    }
    
    /* Ensure text is visible in both light and dark modes */
    h1, h2, h3 {
        color: var(--text-color) !important;
    }
    
    /* Force contrast for title specifically */
    [data-testid="stApp"] h1 {
        color: inherit !important;
    }
    
    /* Ensure proper contrast for all text elements */
    .stMarkdown, p, span, div {
        color: inherit;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Header
st.title("📖 Book of Mormon Daily Reader")
st.caption("Daily reading in 365 days")

# Load verses
all_verses = load_verses()

# Compact date selector at top
col1, col2 = st.columns([2, 1])
with col1:
    selected_date = st.date_input(
        "📅 Select Date",
        value=datetime.now(),
        min_value=datetime(datetime.now().year, 1, 1),
        max_value=datetime(datetime.now().year, 12, 31),
        label_visibility="collapsed"
    )

with col2:
    day_of_year = get_day_of_year(selected_date)
    st.metric("Day", f"{day_of_year}/365", label_visibility="visible")

# Progress bar
progress = day_of_year / 365
st.progress(progress, text=f"Progress: {progress*100:.0f}%")

# Dataset status notice
if len(all_verses) < 100:
    st.warning("⚠️ Demo Mode: Place book_of_mormon.json in the same directory.")
else:
    st.info(f"✅ {len(all_verses)} verses loaded")

# Get today's verses
todays_verses = get_verses_for_day(day_of_year, all_verses)

# Day header
start_verse = (day_of_year - 1) * VERSES_PER_DAY + 1
end_verse = min(start_verse + VERSES_PER_DAY - 1, TOTAL_VERSES)
st.subheader(f"{selected_date.strftime('%B %d, %Y')}")
st.caption(f"Verses {start_verse}–{end_verse}")
st.divider()

# Display verses
for verse in todays_verses:
    reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
    st.markdown(f"### {reference}")
    
    # Split verse into phrases
    english_phrases = split_into_phrases(verse['english'])
    
    # Create a container for phrase-by-phrase display
    for i, eng_phrase in enumerate(english_phrases):
        # Create a subtle container for each phrase pair
        with st.container():
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"<span style='color: #3b82f6;'><strong>EN:</strong></span> {eng_phrase}", unsafe_allow_html=True)
            
            with col2:
                italian_phrase = translate_to_italian(eng_phrase)
                st.markdown(f"<span style='color: #ef4444;'><strong>IT:</strong></span> {italian_phrase}", unsafe_allow_html=True)
            
            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
    
    # Audio for complete verse
    st.markdown("---")
    col_audio_label, col_audio_player = st.columns([3, 1])
    with col_audio_label:
        st.markdown("**🔊 Listen to complete verse in Italian:**")
    with col_audio_player:
        full_italian = translate_to_italian(verse['english'])
        if not full_italian.startswith("["):
            audio_data = text_to_speech(full_italian)
            if audio_data:
                st.audio(audio_data, format='audio/mp3')
    
    st.divider()

# Footer
st.caption(f"📚 Book of Mormon | Day {day_of_year} of 365")