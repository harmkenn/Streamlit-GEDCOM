import streamlit as st
import pandas as pd
from typing import Dict, Tuple, Any, Optional
import re
from thefuzz import fuzz

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Genealogy Workbench")

# ==============================================================================
# SECTION 1: SHARED CORE FUNCTIONS (DEFINED ONCE FOR ALL TOOLS)
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
            continue # Skip malformed lines
        
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
def generate_individual_dataset(individuals: Dict[str, Any], families: Dict[str, Any]) -> pd.DataFrame:
    """Builds a clean dataset of individuals with date formatting and parent lookup."""
    rows = []
    
    @st.cache_data
    def get_person_name(_individuals, ind_id: Optional[str]) -> Optional[str]:
        if not ind_id or not isinstance(ind_id, str): return None
        person_data = _individuals.get(ind_id.strip('@'), {})
        name = person_data.get("NAME", [None])[0]
        return name.replace("/", "") if isinstance(name, str) else None

    def format_gedcom_date(date_str: Optional[str]) -> Optional[str]:
        if not date_str: return None
        clean_date_str = re.sub(r'^(ABT|EST|CAL|INT|BEF|AFT|FROM|TO)\s+', '', str(date_str).strip(), flags=re.IGNORECASE)
        clean_date_str = re.sub(r'^BET\s+(.*?)\s+AND.*', r'\1', clean_date_str, flags=re.IGNORECASE)
        dt_object = pd.to_datetime(clean_date_str, errors='coerce')
        return dt_object.strftime('%Y-%m-%d') if pd.notna(dt_object) else None

    for ind_id, data in individuals.items():
        famc_id = (data.get("FAMC", [None])[0] or "").strip('@')
        father_id, mother_id = None, None
        if famc_id:
            family_data = families.get(famc_id, {})
            father_id = (family_data.get("HUSB", [None])[0] or "").strip('@')
            mother_id = (family_data.get("WIFE", [None])[0] or "").strip('@')
        rows.append({
            "ID Number": ind_id,
            "Full Name": get_person_name(individuals, ind_id),
            "Gender": data.get("SEX", [None])[0],
            "Birth Date": format_gedcom_date(data.get("BIRT_DATE", [None])[0]),
            "Death Date": format_gedcom_date(data.get("DEAT_DATE", [None])[0]),
            "Father's Full Name": get_person_name(individuals, father_id),
            "Mother's Full Name": get_person_name(individuals, mother_id),
        })
    return pd.DataFrame(rows)

@st.cache_data
def find_all_descendants(_individuals: Dict, _families: Dict, start_person_id: str, max_generations: int) -> set:
    """Finds all descendants of a given person."""
    if not start_person_id: return set()
    descendant_ids = set()
    queue = [(start_person_id, 1)]
    processed_ids = {start_person_id}
    while queue:
        current_id, generation = queue.pop(0)
        descendant_ids.add(current_id)
        if generation >= max_generations: continue
        person_data = _individuals.get(current_id, {})
        for fam_id in person_data.get("FAMS", []):
            family_data = _families.get(fam_id.strip('@'), {})
            for child_id in family_data.get("CHIL", []):
                child_id_clean = child_id.strip('@')
                if child_id_clean and child_id_clean not in processed_ids:
                    processed_ids.add(child_id_clean)
                    queue.append((child_id_clean, generation + 1))
    return descendant_ids

# ==============================================================================
# SECTION 2: UI PAGES FOR EACH TOOL
# ==============================================================================

def display_gedcom_processor(tool_name: str, key_prefix: str):
    """Generic function to render a GEDCOM processing page."""
    st.header(f"🗂️ {tool_name} GEDCOM Processor")
    st.write(f"Upload a {tool_name} GEDCOM file to create a special list and save it for comparison.")
    
    uploaded_file = st.file_uploader(f"Upload {tool_name} GEDCOM", type=["ged", "txt"], key=f"{key_prefix}_upload")
    
    if not uploaded_file: return

    try:
        contents = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        contents = uploaded_file.read().decode("latin-1")

    individuals, families = parse_gedcom(contents)
    if not individuals:
        st.warning("No individuals found in this GEDCOM file.")
        return
        
    dataset = generate_individual_dataset(individuals, families)
    st.success(f"Successfully parsed {len(dataset)} individuals from **{uploaded_file.name}**.")

    # --- Save data to session state for the comparator ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"SAVE AS SOURCE", use_container_width=True):
            st.session_state.source_df = dataset
            st.session_state.source_name = uploaded_file.name
            st.success("✅ Saved as Source for comparison.")
    with col2:
        if st.button(f"SAVE AS TARGET", use_container_width=True):
            st.session_state.target_df = dataset
            st.session_state.target_name = uploaded_file.name
            st.success("✅ Saved as Target for comparison.")
    
    st.markdown("---")

    # --- Descendant Analysis ---
    st.subheader("Descendant Analysis")
    name_list = dataset.dropna(subset=['Full Name']).apply(lambda r: f"{r['Full Name']} (ID: {r['ID Number']})", axis=1).tolist()
    
    if not name_list:
        st.warning("No named individuals available for descendant analysis.")
        return

    selected_person_str = st.selectbox("Select an individual to find descendants:", name_list, key=f"{key_prefix}_select")
    if selected_person_str:
        start_id = re.search(r'\(ID: (.*?)\)', selected_person_str).group(1)
        with st.spinner("Finding descendants..."):
            desc_ids = find_all_descendants(individuals, families, start_id, 7)
            desc_df = dataset[dataset['ID Number'].isin(desc_ids)]
        st.write(f"Found **{len(desc_df)}** descendants.")
        st.dataframe(desc_df, use_container_width=True)
        st.download_button("⬇️ Download Descendant List", desc_df.to_csv(index=False).encode('utf-8'), f"descendants_of_{start_id}.csv")

def page_comparator():
    """Page for comparing two datasets."""
    st.header("🔬 Genealogy Comparator")
    st.write("Find people from the Source list who are missing from the Target list.")

    # --- Load data from session state ---
    col1, col2 = st.columns(2)
    with col1:
        if 'source_df' in st.session_state and st.session_state.source_df is not None:
            st.success(f"✅ SOURCE LOADED: **{st.session_state.source_name}** ({len(st.session_state.source_df)} rows)")
            source_df = st.session_state.source_df
        else:
            st.warning("No Source data loaded. Please process a GEDCOM and 'Save as Source'.")
            return
    with col2:
        if 'target_df' in st.session_state and st.session_state.target_df is not None:
            st.success(f"✅ TARGET LOADED: **{st.session_state.target_name}** ({len(st.session_state.target_df)} rows)")
            target_df = st.session_state.target_df
        else:
            st.warning("No Target data loaded. Please process a GEDCOM and 'Save as Target'.")
            return
            
    st.markdown("---")

    # --- Matching Configuration ---
    st.sidebar.header("⚙️ Matching Settings")
    name_threshold = st.sidebar.slider("Name Similarity Threshold (%)", 50, 100, 85)
    year_tolerance = st.sidebar.slider("Year Tolerance (+/- Years)", 0, 10, 1)

    if st.button("🚀 Run Comparison", use_container_width=True):
        with st.spinner("Comparing records... This may take a moment."):
            
            def get_year(date_str: Any) -> Optional[int]:
                if pd.isna(date_str) or not isinstance(date_str, str): return None
                try: return pd.to_datetime(date_str, errors='coerce').year
                except: return None
            
            # Pre-process a copy of the dataframes
            source = source_df.copy()
            target = target_df.copy()

            source['birth_year'] = source['Birth Date'].apply(get_year)
            source['death_year'] = source['Death Date'].apply(get_year)
            
            target_list = [
                (row['Full Name'].lower().strip(), get_year(row['Birth Date']), get_year(row['Death Date']))
                for _, row in target.iterrows()
            ]

            missing_people_indices = []
            for index, source_person in source.iterrows():
                found_match = False
                sp_name = source_person['Full Name'].lower().strip()
                sp_birth = source_person['birth_year']
                sp_death = source_person['death_year']

                for tp_name, tp_birth, tp_death in target_list:
                    if fuzz.ratio(sp_name, tp_name) < name_threshold:
                        continue
                    if sp_birth and tp_birth and abs(sp_birth - tp_birth) > year_tolerance:
                        continue
                    if sp_death and tp_death and abs(sp_death - tp_death) > year_tolerance:
                        continue
                    found_match = True
                    break
                
                if not found_match:
                    missing_people_indices.append(index)

        st.success(f"Comparison Complete! Found **{len(missing_people_indices)}** people from the Source who are likely missing from the Target.")
        if missing_people_indices:
            missing_df = source_df.loc[missing_people_indices]
            st.dataframe(missing_df, use_container_width=True)
            st.download_button("⬇️ Download Missing Persons CSV", missing_df.to_csv(index=False).encode('utf-8'), "missing_persons.csv")

# ==============================================================================
# SECTION 3: MAIN APP NAVIGATION
# ==============================================================================

st.sidebar.title("Genealogy Workbench")
st.sidebar.write("v2026.1 by Ken Harmon")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "CHOOSE A TOOL",
    ["Ancestry Processor", "FamilySearch Processor", "Genealogy Comparator"]
)

if app_mode == "Ancestry Processor":
    display_gedcom_processor("Ancestry", "anc")
elif app_mode == "FamilySearch Processor":
    display_gedcom_processor("FamilySearch", "fs")
elif app_mode == "Genealogy Comparator":
    page_comparator()
