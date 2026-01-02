import streamlit as st
import pandas as pd
from typing import Dict, Tuple, Any, Optional
import re
from thefuzz import fuzz

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Genealogy Workbench")

# ==============================================================================
# SECTION 1: SHARED CORE FUNCTIONS (DEFINED ONCE FOR ALL TOOLS) v1.0
# These are cached to prevent re-computation on the same file.
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
                current_id = parts[1].strip("@")
                current_type = parts[2]
                records, last_tag_info = {}, {}
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
            if parent_tag is None or p_idx is None: continue
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
    """Builds a clean dataset of individuals with date formatting and parent lookup."""
    rows = []
    
    # Memoized function for names to speed up parent lookups
    _name_cache = {}
    def get_person_name(ind_id: Optional[str]) -> Optional[str]:
        if not ind_id or not isinstance(ind_id, str): return None
        ind_id_clean = ind_id.strip('@')
        if ind_id_clean in _name_cache: return _name_cache[ind_id_clean]
        
        person_data = _individuals.get(ind_id_clean, {})
        name = (person_data.get("NAME", [None])[0] or "").replace("/", "")
        _name_cache[ind_id_clean] = name
        return name

    def format_gedcom_date(date_str: Optional[str]) -> Optional[str]:
        if not date_str or pd.isna(date_str): return None
        clean_date_str = re.sub(r'^(ABT|EST|CAL|INT|BEF|AFT|FROM|TO)\s+', '', str(date_str).strip(), flags=re.IGNORECASE)
        clean_date_str = re.sub(r'^BET\s+(.*?)\s+AND.*', r'\1', clean_date_str, flags=re.IGNORECASE)
        try:
            dt_object = pd.to_datetime(clean_date_str, errors='coerce')
            return dt_object.strftime('%Y-%m-%d') if pd.notna(dt_object) else None
        except: return None

    for ind_id, data in _individuals.items():
        famc_id = (data.get("FAMC", [None])[0] or "").strip('@')
        father_id, mother_id = None, None
        if famc_id:
            family_data = _families.get(famc_id, {})
            father_id = (family_data.get("HUSB", [None])[0] or "").strip('@')
            mother_id = (family_data.get("WIFE", [None])[0] or "").strip('@')
        rows.append({
            "ID Number": ind_id, "Full Name": get_person_name(ind_id),
            "Gender": data.get("SEX", [None])[0],
            "Birth Date": format_gedcom_date(data.get("BIRT_DATE", [None])[0]),
            "Death Date": format_gedcom_date(data.get("DEAT_DATE", [None])[0]),
            "Father's Full Name": get_person_name(father_id),
            "Mother's Full Name": get_person_name(mother_id),
        })
    return pd.DataFrame(rows)

# ==============================================================================
# SECTION 2: MAIN APPLICATION LAYOUT
# ==============================================================================

st.title("Genealogy Workbench")
st.write("v2026.1 by Ken Harmon")
st.markdown("A unified tool to process, filter, and compare genealogy files from Ancestry and FamilySearch.")
st.markdown("---")

# --- TOOL 1: ANCESTRY PROCESSOR ---
with st.expander("STEP 1: Process Ancestry GEDCOM", expanded=True):
    anc_file = st.file_uploader("Upload Ancestry.com GEDCOM File", type=["ged", "txt"], key="anc_upload")
    if anc_file:
        try:
            anc_contents = anc_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            anc_file.seek(0)
            anc_contents = anc_file.read().decode("latin-1")
            
        anc_individuals, anc_families = parse_gedcom(anc_contents)
        if anc_individuals:
            st.session_state.anc_dataset = generate_individual_dataset(anc_individuals, anc_families)
            st.info(f"Parsed {len(st.session_state.anc_dataset)} individuals from **{anc_file.name}**.")
            
            if st.button("USE THIS AS SOURCE for Comparison", use_container_width=True):
                st.session_state.source_df = st.session_state.anc_dataset
                st.session_state.source_name = anc_file.name
                st.success(f"✅ **{anc_file.name}** is now the SOURCE for comparison.")
                
            st.dataframe(st.session_state.anc_dataset, use_container_width=True, height=300)
        else:
            st.warning("No individuals found in this file.")
            
# --- TOOL 2: FAMILYSEARCH PROCESSOR ---
with st.expander("STEP 2: Process FamilySearch GEDCOM", expanded=True):
    fs_file = st.file_uploader("Upload FamilySearch.com GEDCOM File", type=["ged", "txt"], key="fs_upload")
    if fs_file:
        try:
            fs_contents = fs_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            fs_file.seek(0)
            fs_contents = fs_file.read().decode("latin-1")

        fs_individuals, fs_families = parse_gedcom(fs_contents)
        if fs_individuals:
            st.session_state.fs_dataset = generate_individual_dataset(fs_individuals, fs_families)
            st.info(f"Parsed {len(st.session_state.fs_dataset)} individuals from **{fs_file.name}**.")
            
            if st.button("USE THIS AS TARGET for Comparison", use_container_width=True):
                st.session_state.target_df = st.session_state.fs_dataset
                st.session_state.target_name = fs_file.name
                st.success(f"✅ **{fs_file.name}** is now the TARGET for comparison.")

            st.dataframe(st.session_state.fs_dataset, use_container_width=True, height=300)
        else:
            st.warning("No individuals found in this file.")

# --- TOOL 3: GENEALOGY COMPARATOR ---
with st.expander("STEP 3: Compare Source and Target", expanded=True):
    st.subheader("🔬 Genealogy Comparator")
    st.write("Find people from the Source (Ancestry) who are missing from the Target (FamilySearch).")

    # --- Display status of loaded data ---
    col1, col2 = st.columns(2)
    source_ready = 'source_df' in st.session_state and st.session_state.source_df is not None
    target_ready = 'target_df' in st.session_state and st.session_state.target_df is not None
    
    with col1:
        if source_ready:
            st.success(f"SOURCE READY: **{st.session_state.source_name}**")
        else:
            st.warning("SOURCE NOT LOADED. Process an Ancestry file and click 'Use as Source'.")
    with col2:
        if target_ready:
            st.success(f"TARGET READY: **{st.session_state.target_name}**")
        else:
            st.warning("TARGET NOT LOADED. Process a FamilySearch file and click 'Use as Target'.")
            
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
                
                target_list = [
                    (str(row['Full Name']).lower().strip(), get_year(row['Birth Date']), get_year(row['Death Date']))
                    for _, row in target_df.iterrows()
                ]
                
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
                    
                    if not found_match:
                        missing_indices.append(index)
            
            st.success(f"Comparison Complete! Found **{len(missing_indices)}** people from the Source who are likely missing from the Target.")
            if missing_indices:
                missing_df = source_df.loc[missing_indices]
                st.dataframe(missing_df, use_container_width=True)
                st.download_button("⬇️ Download Missing Persons CSV", missing_df.to_csv(index=False).encode('utf-8'), "missing_persons.csv")
    else:
        st.info("Please load both a Source and a Target dataset to enable the comparison tool.")

