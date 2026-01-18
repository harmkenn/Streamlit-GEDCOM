import streamlit as st
from datetime import datetime
import json
from gtts import gTTS
import base64
from io import BytesIO
import os

# Page config
st.set_page_config(
    page_title="Book of Mormon Daily Reader",
    page_icon="📖",
    layout="wide"
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
        "english": "I, Nephi, having been born of goodly parents, therefore I was taught somewhat in all the learning of my father; and having seen many afflictions in the course of my days, nevertheless, having been highly favored of the Lord in all my days; yea, having had a great knowledge of the goodness and the mysteries of God, therefore I make a record of my proceedings in my days.",
        "italian": "Io, Nefi, essendo nato da buoni genitori, fui quindi istruito in una certa misura in tutta la cultura di mio padre; e avendo avuto molte afflizioni nel corso dei miei giorni, nondimeno, essendo stato grandemente favorito dal Signore in tutti i miei giorni; sì, avendo avuto una grande conoscenza della bontà e dei misteri di Dio, faccio quindi una storia dei miei atti nei miei giorni."
    },
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 2,
        "english": "Yea, I make a record in the language of my father, which consists of the learning of the Jews and the language of the Egyptians.",
        "italian": "Sì, faccio una storia nella lingua di mio padre, che consiste nella cultura dei Giudei e nella lingua degli Egiziani."
    },
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 3,
        "english": "And I know that the record which I make is true; and I make it with mine own hand; and I make it according to my knowledge.",
        "italian": "E so che la storia che faccio è vera; e la faccio di mia propria mano; e la faccio secondo la mia conoscenza."
    },
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 4,
        "english": "For it came to pass in the commencement of the first year of the reign of Zedekiah, king of Judah, (my father, Lehi, having dwelt at Jerusalem in all his days); and in that same year there came many prophets, prophesying unto the people that they must repent, or the great city Jerusalem must be destroyed.",
        "italian": "Poiché avvenne che all'inizio del primo anno del regno di Sedechia, re di Giuda, (mio padre Lehi, avendo dimorato a Gerusalemme per tutti i suoi giorni); e in quello stesso anno vennero molti profeti, profetizzando al popolo che esso doveva pentirsi, o la grande città di Gerusalemme sarebbe stata distrutta."
    }
]

@st.cache_data
def load_verses():
    """Load Book of Mormon verses from JSON file or return sample data"""
    if os.path.exists('book_of_mormon_bilingual.json'):
        try:
            with open('book_of_mormon_bilingual.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return SAMPLE_VERSES
    return SAMPLE_VERSES

def get_day_of_year(date):
    """Calculate day of year from a date"""
    return (date - datetime(date.year, 1, 1)).days + 1

def get_verses_for_day(day_num, all_verses):
    """Get verses for a specific day"""
    start_idx = (day_num - 1) * VERSES_PER_DAY
    end_idx = min(start_idx + VERSES_PER_DAY, len(all_verses))
    return all_verses[start_idx:end_idx] if start_idx < len(all_verses) else all_verses[:VERSES_PER_DAY]

def text_to_speech_link(text, lang='en'):
    """Generate audio link for text using gTTS"""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        b64 = base64.b64encode(audio_bytes.read()).decode()
        return f'<audio controls><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        return f"<p style='color: red;'>Audio error: {str(e)}</p>"

# Custom CSS
st.markdown("""
<style>
    .verse-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #4F46E5;
    }
    .verse-reference {
        color: #4F46E5;
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 10px;
    }
    .english-section {
        background-color: #EFF6FF;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .italian-section {
        background-color: #F0FDF4;
        padding: 15px;
        border-radius: 8px;
    }
    .section-title {
        font-weight: bold;
        margin-bottom: 8px;
    }
    .english-title {
        color: #1E40AF;
    }
    .italian-title {
        color: #166534;
    }
    .header-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-box">
    <h1>📖 Book of Mormon Daily Reader</h1>
    <p>Read the entire Book of Mormon in 365 days with English and Italian text</p>
</div>
""", unsafe_allow_html=True)

# Load verses
all_verses = load_verses()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    selected_date = st.date_input(
        "Select Reading Date",
        value=datetime.now(),
        min_value=datetime(datetime.now().year, 1, 1),
        max_value=datetime(datetime.now().year, 12, 31)
    )
    
    day_of_year = get_day_of_year(selected_date)
    
    st.metric("Day of Year", f"{day_of_year} of 365")
    st.metric("Verses per Day", VERSES_PER_DAY)
    
    progress = day_of_year / 365
    st.progress(progress)
    st.write(f"Progress: {progress*100:.1f}%")
    
    st.divider()
    
    st.subheader("📊 Reading Plan")
    start_verse = (day_of_year - 1) * VERSES_PER_DAY + 1
    end_verse = min(start_verse + VERSES_PER_DAY - 1, TOTAL_VERSES)
    st.write(f"**Today's Verses:** {start_verse}–{end_verse}")
    
    st.divider()
    
    st.subheader("🔊 Audio Options")
    play_english = st.checkbox("Enable English Audio", value=True)
    play_italian = st.checkbox("Enable Italian Audio", value=True)

# Demo notice
st.markdown("""
<div class="info-box">
    <strong>⚠️ Demo Mode:</strong> This app currently shows sample verses from 1 Nephi 1:1-4. 
    To use the full Book of Mormon, replace SAMPLE_VERSES with the complete dataset of 6,604 verses.
    <br><br>
    <strong>Installation Required:</strong> For audio features, install: <code>pip install gtts</code>
</div>
""", unsafe_allow_html=True)

# Get today's verses
todays_verses = get_verses_for_day(day_of_year, all_verses)

# Main content
st.subheader(f"📅 Reading for Day {day_of_year}: {selected_date.strftime('%B %d, %Y')}")

# Display verses
for verse in todays_verses:
    reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
    
    with st.container():
        st.markdown(f'<div class="verse-container">', unsafe_allow_html=True)
        st.markdown(f'<div class="verse-reference">{reference}</div>', unsafe_allow_html=True)
        
        # English section
        st.markdown('<div class="english-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title english-title">English</div>', unsafe_allow_html=True)
        st.write(verse['english'])
        
        if play_english:
            with st.expander("🔊 Play English Audio"):
                audio_html = text_to_speech_link(verse['english'], 'en')
                st.markdown(audio_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Italian section
        st.markdown('<div class="italian-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title italian-title">Italiano</div>', unsafe_allow_html=True)
        st.write(verse['italian'])
        
        if play_italian:
            with st.expander("🔊 Play Italian Audio"):
                audio_html = text_to_speech_link(verse['italian'], 'it')
                st.markdown(audio_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Play all audio section
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button("🔊 Play All English", use_container_width=True):
        all_english = " ".join([v['english'] for v in todays_verses])
        audio_html = text_to_speech_link(all_english, 'en')
        st.markdown(audio_html, unsafe_allow_html=True)

with col2:
    if st.button("🔊 Play All Italian", use_container_width=True):
        all_italian = " ".join([v['italian'] for v in todays_verses])
        audio_html = text_to_speech_link(all_italian, 'it')
        st.markdown(audio_html, unsafe_allow_html=True)

# Footer
st.divider()
st.caption(f"📚 Book of Mormon Daily Reader | Day {day_of_year} of 365 | {VERSES_PER_DAY} verses per day")