import streamlit as st
from datetime import datetime
import json
from gtts import gTTS
import base64
from io import BytesIO
import os

# Try to import translator, install if needed
try:
    from translate import Translator
except ImportError:
    Translator = None

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
        "english": "I, Nephi, having been born of goodly parents, therefore I was taught somewhat in all the learning of my father; and having seen many afflictions in the course of my days, nevertheless, having been highly favored of the Lord in all my days; yea, having had a great knowledge of the goodness and the mysteries of God, therefore I make a record of my proceedings in my days.",
        "italian": "Io, Nefi, essendo nato da buoni genitori, fui quindi istruito in una certa misura in tutta la cultura di mio padre; e avendo avuto molte afflizioni nel corso dei miei giorni, nondimeno, essendo stato grandemente favorito dal Signore in tutti i miei giorni; sì, avendo avuto una grande conoscenza della bontà e dei misteri di Dio, faccio quindi una storia dei miei atti nei miei giorni."
    },
    {
        "book": "1 Nephi",
        "chapter": 1,
        "verse": 2,
        "english": "Yea, I make a record in the language of my father, which consists of the learning of the Jews and the language of the Egyptians.",
        "italian": "Sì, faccio una storia nella lingua di mio padre, che consiste nella cultura dei Giudei e nella lingua degli Egiziani."
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

def translate_italian_word(italian_word):
    """Translate an Italian word to English using available method"""
    italian_word_lower = italian_word.lower()
    
    # Try using translate library first
    if Translator:
        try:
            translator = Translator(from_lang='it', to_lang='en')
            translation = translator.translate(italian_word)
            return translation if translation else italian_word
        except:
            pass
    
    # Fallback: try googletrans
    try:
        from googletrans import Translator as GoogleTranslator
        gt = GoogleTranslator()
        result = gt.translate(italian_word, src_language='it', dest_language='en')
        return result if result else italian_word
    except:
        return "Translation unavailable"

def get_day_of_year(date):
    """Calculate day of year from a date"""
    from datetime import date as date_class
    start_of_year = date_class(date.year, 1, 1)
    return (date - start_of_year).days + 1

def get_verses_for_day(day_num, all_verses):
    """Get verses for a specific day"""
    start_idx = (day_num - 1) * VERSES_PER_DAY
    end_idx = min(start_idx + VERSES_PER_DAY, len(all_verses))
    return all_verses[start_idx:end_idx] if start_idx < len(all_verses) else all_verses[:VERSES_PER_DAY]

def text_to_speech_link(text, lang='it'):
    """Generate audio link for text using gTTS"""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        b64 = base64.b64encode(audio_bytes.read()).decode()
        return f'<audio controls style="width: 100%; max-width: 100%;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        return f"<p style='color: red; font-size: 0.9em;'>Audio error: {str(e)}</p>"

def make_text_interactive(text, verse_id, language='en'):
    """Convert text into clickable words with translation capability"""
    import re
    import json
    
    # Split on whitespace and punctuation, keeping punctuation
    words = re.findall(r'\b\w+\b|\W+', text)
    html = []
    word_index = 0
    
    for item in words:
        if re.match(r'\w+', item):  # Is a word
            if language == 'it':
                # Create unique ID for each word instance
                word_id = f"{verse_id}_word_{word_index}_{item}"
                # Italian words are clickable for translation - use button instead
                html.append(f'<button class="italian-word-btn" data-word="{item}" data-word-id="{word_id}" style="background: none; border: none; color: #059669; cursor: pointer; padding: 0; border-bottom: 1px dotted #059669; font-size: inherit; font-family: inherit;" title="Click for translation">{item}</button>')
            else:
                # English words are just displayed
                html.append(f'<span>{item}</span>')
            word_index += 1
        else:  # Is punctuation/whitespace
            html.append(item)
    
    return ''.join(html)

# JavaScript for word translation
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Attach click handlers to all Italian word buttons
    document.querySelectorAll('.italian-word-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const word = this.getAttribute('data-word');
            window.parent.postMessage({type: 'translate-word', word: word}, '*');
        });
    });
});
</script>
""", unsafe_allow_html=True)


# Mobile-optimized CSS
st.markdown("""
<style>
    /* Force light mode */
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
    
    /* Mobile-first responsive design */
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
    
    .word-clickable {
        cursor: pointer;
        padding: 2px 4px;
        border-radius: 3px;
        transition: all 0.2s ease;
        user-select: none;
    }
    
    .word-clickable:hover {
        background-color: #DBEAFE;
    }
    
    .word-highlighted {
        background-color: #FCD34D;
        font-weight: bold;
        border: 1px solid #F59E0B;
    }
    
    .english-section {
        background-color: #F3F4F6;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        font-size: 0.95em;
        line-height: 1.6;
        color: #262730 !important;
    }
    
    .italian-section {
        background-color: #ECFDF5;
        padding: 12px;
        border-radius: 6px;
        font-size: 0.95em;
        line-height: 1.6;
        color: #262730 !important;
    }
    
    .section-title {
        font-weight: bold;
        margin-bottom: 8px;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .english-title {
        color: #6B7280;
    }
    
    .italian-title {
        color: #059669;
    }
    
    .header-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px 15px;
        border-radius: 8px;
        color: white;
        margin-bottom: 16px;
        text-align: center;
    }
    
    .header-box h1 {
        font-size: 1.5em;
        margin-bottom: 5px;
    }
    
    .header-box p {
        font-size: 0.9em;
        margin: 0;
    }
    
    .info-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 12px;
        border-radius: 5px;
        margin-bottom: 16px;
        font-size: 0.9em;
    }
    
    .success-box {
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 12px;
        border-radius: 5px;
        margin-bottom: 16px;
        font-size: 0.9em;
    }
    
    .day-header {
        background-color: #F9FAFB;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 16px;
        text-align: center;
        border: 1px solid #E5E7EB;
    }
    
    /* Make buttons full width on mobile */
    .stButton > button {
        width: 100%;
        margin-bottom: 8px;
    }
    
    /* Improve date picker for mobile */
    .stDateInput {
        width: 100%;
    }
    
    /* Hide Streamlit branding on mobile */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Compact expander for audio */
    .streamlit-expanderHeader {
        font-size: 0.9em;
        padding: 8px;
    }
    
    /* Audio player styling */
    audio {
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-box">
    <h1>📖 Libro di Mormon</h1>
    <p>Lettura quotidiana in 365 giorni</p>
</div>
""", unsafe_allow_html=True)

# Initialize translation cache
if 'translation_cache' not in st.session_state:
    st.session_state.translation_cache = {}

if 'pending_translation' not in st.session_state:
    st.session_state.pending_translation = None

# Handle translation display at the top
translation_col = st.empty()

# Check if we need to translate a word (from query params or session)
if st.session_state.pending_translation:
    word = st.session_state.pending_translation
    if word not in st.session_state.translation_cache:
        # Translate the word
        try:
            translation = translate_italian_word(word)
            st.session_state.translation_cache[word] = translation
        except:
            st.session_state.translation_cache[word] = "Error translating"
    
    # Display the translation
    trans = st.session_state.translation_cache[word]
    with translation_col:
        st.info(f"**{word.title()}**: {trans}")
    
    st.session_state.pending_translation = None

# Load verses
all_verses = load_verses()

# Compact date selector at top
col1, col2 = st.columns([2, 1])
with col1:
    selected_date = st.date_input(
        "📅 Seleziona Data",
        value=datetime.now(),
        min_value=datetime(datetime.now().year, 1, 1),
        max_value=datetime(datetime.now().year, 12, 31),
        label_visibility="collapsed"
    )
with col2:
    day_of_year = get_day_of_year(selected_date)
    st.metric("Giorno", f"{day_of_year}/365", label_visibility="visible")

# Progress bar
progress = day_of_year / 365
st.progress(progress, text=f"Progresso: {progress*100:.0f}%")

# Dataset status notice
if len(all_verses) < 100:
    st.markdown("""
    <div class="info-box">
        <strong>⚠️ Modalità Demo</strong><br>
        Posiziona book_of_mormon_bilingual.json nella stessa directory.
    </div>
    """, unsafe_allow_html=True)
else:
    verses_with_italian = sum(1 for v in all_verses if v.get('italian', ''))
    percentage = verses_with_italian / len(all_verses) * 100
    st.markdown(
        f'<div class="success-box">'
        f'<strong>✅ Dataset Completo Caricato!</strong><br>'
        f'Versetti: {len(all_verses)} | Italiano: {percentage:.0f}%'
        f'</div>',
        unsafe_allow_html=True
    )

# Get today's verses
todays_verses = get_verses_for_day(day_of_year, all_verses)

# Day header
start_verse = (day_of_year - 1) * VERSES_PER_DAY + 1
end_verse = min(start_verse + VERSES_PER_DAY - 1, TOTAL_VERSES)
st.markdown(
    f'<div class="day-header">'
    f'<strong>{selected_date.strftime("%d %B %Y")}</strong><br>'
    f'<small>Versetti {start_verse}–{end_verse}</small>'
    f'</div>',
    unsafe_allow_html=True
)

# Italian audio for all verses button
if st.button("🔊 Ascolta Tutti i Versetti in Italiano", use_container_width=True):
    all_italian = " ".join([v.get('italian', '') for v in todays_verses if v.get('italian', '')])
    if all_italian:
        audio_html = text_to_speech_link(all_italian, 'it')
        st.markdown(audio_html, unsafe_allow_html=True)
    else:
        st.warning("Nessun testo italiano disponibile")

st.divider()

# Display verses
for idx, verse in enumerate(todays_verses):
    reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
    verse_id = f"verse_{idx}_{verse['chapter']}_{verse['verse']}"
    
    st.markdown(f'<div class="verse-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="verse-reference">{reference}</div>', unsafe_allow_html=True)
    
    # Side-by-side English and Italian with interactive words
    col_en, col_it = st.columns(2)
    
    with col_en:
        st.markdown('<div class="section-title english-title">English</div>', unsafe_allow_html=True)
        english_interactive = make_text_interactive(verse["english"], verse_id, 'en')
        st.markdown(f'<div class="english-section" style="line-height: 1.8;">{english_interactive}</div>', unsafe_allow_html=True)
    
    with col_it:
        st.markdown('<div class="section-title italian-title">Italiano</div>', unsafe_allow_html=True)
        italian_interactive = make_text_interactive(verse.get('italian', ''), verse_id, 'it')
        st.markdown(f'<div class="italian-section" style="line-height: 1.8;">{italian_interactive}</div>', unsafe_allow_html=True)
    
    # Italian audio for individual verse
    if verse.get('italian', ''):
        with st.expander("🔊 Ascolta questo versetto", expanded=True):
            audio_html = text_to_speech_link(verse['italian'], 'it')
            st.markdown(audio_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.divider()
st.caption(f"📚 Libro di Mormon | Giorno {day_of_year} di 365")

# Hidden component to handle translation requests via JavaScript
def show_translations():
    """Display cached translations as JSON for JavaScript to use"""
    if st.session_state.translation_cache:
        st.markdown(f"""
        <script>
        window.translationCache = {json.dumps(st.session_state.translation_cache)};
        </script>
        """, unsafe_allow_html=True)

show_translations()