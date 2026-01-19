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
    """Translate English text to Italian using googletrans"""
    try:
        from googletrans import Translator
        translator = Translator()
        translation = translator.translate(text, src='en', dest='it')
        return translation.text
    except ImportError:
        return "[Translation unavailable - install googletrans: pip install googletrans==3.1.0a0]"
    except Exception as e:
        return f"[Translation error: {str(e)}]"

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

# Mobile-optimized CSS
st.markdown("""
<style>
    [data-testid="stApp"] {
        background-color: #FFFFFF !important;
    }
    
    [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
    }
    
    body {
        background-color: #FFFFFF !important;
        color: #262730 !important;
    }
    
    .main > div {
        padding-top: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    .verse-container {
        background-color: #ffffff;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 3px solid #4F46E5;
    }
    
    .verse-reference {
        color: #4F46E5;
        font-weight: bold;
        font-size: 1em;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .verse-text {
        font-size: 0.95em;
        line-height: 1.6;
        color: #262730;
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
    
    # English version
    st.markdown("**English**")
    st.markdown(f"<div class='verse-text'>{verse['english']}</div>", unsafe_allow_html=True)
    
    # Italian translation (cached)
    st.markdown("**Italiano**")
    italian_text = translate_to_italian(verse['english'])
    
    # Create columns for text and audio button
    col_text, col_audio = st.columns([4, 1])
    
    with col_text:
        st.markdown(f"<div class='verse-text'>{italian_text}</div>", unsafe_allow_html=True)
    
    with col_audio:
        if not italian_text.startswith("["):  # Only show audio if translation succeeded
            audio_data = text_to_speech(italian_text)
            if audio_data:
                st.audio(audio_data, format='audio/mp3')
            else:
                st.caption("🔊 Install gTTS: pip install gtts")
    
    st.divider()

# Footer
st.caption(f"📚 Book of Mormon | Day {day_of_year} of 365")