import streamlit as st
import pandas as pd
from typing import Dict, Tuple, Any, Optional
import re
from thefuzz import fuzz

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Genealogy Workbench")

# ==============================================================================
# SECTION 1: SHARED CORE FUNCTIONS (DEFINED ONCE) v2.0
# ==============================================================================

@st.cache_data
def parse_gedcom(file_contents: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Parses GEDCOM file contents and extracts individuals and families."""
    individuals: Dict[str, Any] = {}
    families: Dict[str, Any] = {}
    current_id: Optional[str] = None
    current_type: Optional[str] = None
    records: Dict[str, Any] = {}
    last_tag_info: Dict[str, Any] = {}
    lines = file_contents.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line: continue
        try:
            parts = line.split(" ", 2)
            level = int(parts[0])
        except (ValueError, IndexError):
            continue
        
        if level == 0:
            if current_id and current_type:
                if current_type == "INDI": individuals[current_id] = records
                elif current_type == "FAM": families[current_id] = records
            if len(parts) > 2 and parts[2] in ("INDI", "FAM"):
                current_id, current_type, records, last_tag_info = parts[1].strip("@"), parts[2], {}, {}
            else:
                current_id, current_type = None, None
        
        if not current_id: continue
        tag = parts[1].strip()
        value = parts[2] if len(parts) > 2 else ""
        if level == 1:
            if tag not in records: records[tag] = []
            records[tag].append(value)
            last_tag_info = {"tag": tag, "index": len(records[tag]) - 1}
        elif level > 1 and last_tag_info:
            parent_tag, p_idx = last_tag_info.get("tag"), last_tag_info.get("index")
            if p_idx is not None and parent_tag is not None:
                if tag == "CONC": records[parent_tag][p_idx] += value
                elif tag == "CONT": records[parent_tag][p_idx] += "\n" + value
                else:
                    full_tag = f"{parent_tag}_{tag}"
                    if full_tag not in records: records[full_tag] = []
                    records[full_tag].append(value)

    if current_id and current_type:
        if current_type == "INDI": individuals[current_id] = records
        elif current_type == "FAM": families[current_id] = records
    return individuals, families

@st.cache_data
def generate_individual_dataset(_individuals: Dict[str, Any], _families: Dict[str, Any]) -> pd.DataFrame:
    """Builds a clean dataset of individuals from parsed GEDCOM data."""
    rows = []
    _name_cache = {}
    def get_person_name(ind_id: Optional[str]) -> Optional[str]:
        if not ind_id or pd.isna(ind_id): return None
        ind_id_clean = str(ind_id).strip('@')
        if ind_id_clean in _name_cache: return _name_cache[ind_id_clean]
        name = (_individuals.get(ind_id_clean, {}).get("NAME", [None])[0] or "").replace("/", "")
        _name_cache[ind_id_clean] = name
        return name

    def format_gedcom_date(date_str: Any) -> Optional[str]:
        if pd.isna(date_str): return None
        clean_date_str = re.sub(r'^(ABT|EST|CAL|INT|BEF|AFT|FROM|TO)\s+', '', str(date_str).strip(), flags=re.IGNORECASE)
        clean_date_str = re.sub(r'^BET\s+(.*?)\s+AND.*', r'\1', clean_date_str, flags=re.IGNORECASE)
        try:
            return pd.to_datetime(clean_date_str, errors='coerce').strftime('%Y-%m-%d')
        except: return None

    for ind_id, data in _individuals.items():
        famc_id = (data.get("FAMC", [None])[0] or "").strip('@')
        father_id, mother_id = None, None
        if famc_id:
            family_data = _families.get(famc_id, {})
            father_id = (family_data.get("HUSB", [None])[0] or "").strip('@')
            mother_id = (family_data.get("WIFE", [None])[0] or "").strip('@')
        rows.append({
            "ID Number": ind_id, "Full Name": get_person_name(ind_id), "Gender": data.get("SEX", [None])[0],
            "Birth Date": format_gedcom_date(data.get("BIRT_DATE", [None])[0]),
            "Death Date": format_gedcom_date(data.get("DEAT_DATE", [None])[0]),
            "Father's Full Name": get_person_name(father_id), "Mother's Full Name": get_person_name(mother_id),
        })
    return pd.DataFrame(rows)

# ==============================================================================
# SECTION 2: REUSABLE UI AND MAIN LAYOUT
# ==============================================================================

def create_processor_ui(title: str, upload_label: str, button_label: str, session_df_key: str, session_name_key: str, uploader_key: str):
    """Creates a UI for processing either a GEDCOM or a CSV file."""
    with st.expander(title, expanded=True):
        uploaded_file = st.file_uploader(upload_label, type=["ged", "txt", "csv"], key=uploader_key)
        
        if uploaded_file:
            dataset = None
            # --- Smart File Handling ---
            if uploaded_file.name.lower().endswith('.csv'):
                with st.spinner("Loading CSV..."):
                    dataset = pd.read_csv(uploaded_file)
                st.info(f"Loaded {len(dataset)} rows from CSV: **{uploaded_file.name}**")
            else: # Assume GEDCOM
                with st.spinner("Parsing GEDCOM..."):
                    try:
                        contents = uploaded_file.read().decode("utf-8-sig")
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        contents = uploaded_file.read().decode("latin-1")
                    
                    individuals, families = parse_gedcom(contents)
                    if individuals:
                        dataset = generate_individual_dataset(individuals, families)
                        st.info(f"Parsed {len(dataset)} individuals from GEDCOM: **{uploaded_file.name}**")
                    else:
                        st.warning("No individuals found in this GEDCOM file.")
            
            if dataset is not None:
                if st.button(button_label, use_container_width=True, key=f"{uploader_key}_button"):
                    st.session_state[session_df_key] = dataset
                    st.session_state[session_name_key] = uploaded_file.name
                    st.success(f"✅ **{uploaded_file.name}** is now the {session_df_key.split('_')[0].upper()} for comparison.")
                
                st.dataframe(dataset, use_container_width=True, height=300)

# --- Main Page Layout ---
st.title("Genealogy Workbench")
st.write("v2026.1 by Ken Harmon")
st.markdown("A unified tool to process, filter, and compare genealogy files from Ancestry and FamilySearch.")
st.markdown("---")

# --- Render UI Components ---
create_processor_ui(
    title="STEP 1: Process Ancestry File (GEDCOM or CSV)",
    upload_label="Upload Ancestry File",
    button_label="USE THIS AS SOURCE for Comparison",
    session_df_key='source_df',
    session_name_key='source_name',
    uploader_key='anc_uploader'
)

create_processor_ui(
    title="STEP 2: Process FamilySearch File (GEDCOM or CSV)",
    upload_label="Upload FamilySearch File",
    button_label="USE THIS AS TARGET for Comparison",
    session_df_key='target_df',
    session_name_key='target_name',
    uploader_key='fs_uploader'
)

# --- TOOL 3: GENEALOGY COMPARATOR ---
with st.expander("STEP 3: Compare Source and Target", expanded=True):
    st.subheader("🔬 Genealogy Comparator")
    st.write("Find people from the Source who are missing from the Target.")

    col1, col2 = st.columns(2)
    source_ready = 'source_df' in st.session_state and st.session_state.source_df is not None
    target_ready = 'target_df' in st.session_state and st.session_state.target_df is not None
    
    with col1:
        if source_ready: st.success(f"SOURCE READY: **{st.session_state.source_name}**")
        else: st.warning("SOURCE NOT LOADED.")
    with col2:
        if target_ready: st.success(f"TARGET READY: **{st.session_state.target_name}**")
        else: st.warning("TARGET NOT LOADED.")
            
    st.markdown("---")

    if source_ready and target_ready:
        st.sidebar.header("⚙️ Matching Settings")
        name_threshold = st.sidebar.slider("Name Similarity Threshold (%)", 50, 100, 85, key="comp_name")
        year_tolerance = st.sidebar.slider("Year Tolerance (+/-)", 0, 10, 1, key="comp_year")
        
        if st.button("🚀 Run Comparison", use_container_width=True):
            with st.spinner("Comparing records... This might take a moment."):
                source_df = st.session_state.source_df.copy()
                target_df = st.session_state.target_df.copy()

                def get_year(date_str: Any) -> Optional[int]:
                    if pd.isna(date_str): return None
                    try: return pd.to_datetime(date_str, errors='coerce').year
                    except: return None
                
                target_list = [(str(row['Full Name']).lower().strip(), get_year(row['Birth Date']), get_year(row['Death Date'])) for _, row in target_df.iterrows()]
                missing_indices = []
                for index, source_person in source_df.iterrows():
                    found_match = False
                    sp_name = str(source_person['Full Name']).lower().strip()
                    sp_birth = get_year(source_person['Birth Date'])
                    sp_death = get_year(source_person['Death Date'])

                    for tp_name, tp_birth, tp_death in target_list:
                        if fuzz.ratio(sp_name, tp_name) < name_threshold: continue
                        if sp_birth and tp_birth and abs(sp_birth - tp_birth) > year_tolerance: continue
                        if sp_death and tp_death and abs(sp_death - tp_death) > year_tolerance: continue
                        found_match = True
                        break
                    if not found_match: missing_indices.append(index)
            
            st.success(f"Comparison Complete! Found **{len(missing_indices)}** people from the Source who are likely missing from the Target.")
            if missing_indices:
                missing_df = source_df.loc[missing_indices]
                st.dataframe(missing_df, use_container_width=True)
                st.download_button("⬇️ Download Missing Persons CSV", missing_df.to_csv(index=False).encode('utf-8'), "missing_persons.csv")
    else:
        st.info("Please load both a Source and a Target dataset to enable the comparison tool.")

