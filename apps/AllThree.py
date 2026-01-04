import streamlit as st
import pandas as pd
from typing import Dict, Tuple, Any, Optional, List
import re
from datetime import datetime
import io

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Genealogy Workbench", page_icon="🌳")

# ==============================================================================
# SECTION 1: SHARED CORE FUNCTIONS v3.0
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
        if not line:
            continue
        
        try:
            parts = line.split(" ", 2)
            level = int(parts[0])
        except (ValueError, IndexError):
            continue
        
        if level == 0:
            if current_id and current_type:
                if current_type == "INDI":
                    individuals[current_id] = records
                elif current_type == "FAM":
                    families[current_id] = records
            
            if len(parts) > 2 and parts[2] in ("INDI", "FAM"):
                current_id = parts[1].strip("@")
                current_type = parts[2]
                records = {}
                last_tag_info = {}
            else:
                current_id = None
                current_type = None
        
        if not current_id:
            continue
        
        tag = parts[1].strip()
        value = parts[2] if len(parts) > 2 else ""
        
        if level == 1:
            if tag not in records:
                records[tag] = []
            records[tag].append(value)
            last_tag_info = {"tag": tag, "index": len(records[tag]) - 1}
        elif level > 1 and last_tag_info:
            parent_tag = last_tag_info.get("tag")
            p_idx = last_tag_info.get("index")
            if p_idx is not None and parent_tag is not None:
                if tag == "CONC":
                    records[parent_tag][p_idx] += value
                elif tag == "CONT":
                    records[parent_tag][p_idx] += "\n" + value
                else:
                    full_tag = f"{parent_tag}_{tag}"
                    if full_tag not in records:
                        records[full_tag] = []
                    records[full_tag].append(value)

    if current_id and current_type:
        if current_type == "INDI":
            individuals[current_id] = records
        elif current_type == "FAM":
            families[current_id] = records
    
    return individuals, families

@st.cache_data
def generate_individual_dataset(_individuals: Dict[str, Any], _families: Dict[str, Any]) -> pd.DataFrame:
    """Builds a clean dataset of individuals from parsed GEDCOM data."""
    rows = []
    _name_cache = {}
    
    def get_person_name(ind_id: Optional[str]) -> Optional[str]:
        if not ind_id or pd.isna(ind_id):
            return None
        ind_id_clean = str(ind_id).strip('@')
        if ind_id_clean in _name_cache:
            return _name_cache[ind_id_clean]
        name = (_individuals.get(ind_id_clean, {}).get("NAME", [None])[0] or "").replace("/", "")
        _name_cache[ind_id_clean] = name
        return name

    def format_gedcom_date(date_str: Any) -> Optional[str]:
        if pd.isna(date_str):
            return None
        clean_date_str = re.sub(r'^(ABT|EST|CAL|INT|BEF|AFT|FROM|TO)\s+', '', str(date_str).strip(), flags=re.IGNORECASE)
        clean_date_str = re.sub(r'^BET\s+(.*?)\s+AND.*', r'\1', clean_date_str, flags=re.IGNORECASE)
        try:
            return pd.to_datetime(clean_date_str, errors='coerce').strftime('%Y-%m-%d')
        except:
            return None

    for ind_id, data in _individuals.items():
        famc_id = (data.get("FAMC", [None])[0] or "").strip('@')
        father_id, mother_id = None, None
        if famc_id:
            family_data = _families.get(famc_id, {})
            father_id = (family_data.get("HUSB", [None])[0] or "").strip('@')
            mother_id = (family_data.get("WIFE", [None])[0] or "").strip('@')
        
        rows.append({
            "ID Number": ind_id,
            "Full Name": get_person_name(ind_id),
            "Gender": data.get("SEX", [None])[0],
            "Birth Date": format_gedcom_date(data.get("BIRT_DATE", [None])[0]),
            "Death Date": format_gedcom_date(data.get("DEAT_DATE", [None])[0]),
            "Father's Full Name": get_person_name(father_id),
            "Mother's Full Name": get_person_name(mother_id),
            "FamilySearch ID": data.get("_FSFTID", [None])[0],
        })
    
    return pd.DataFrame(rows)

def get_year(date_str) -> Optional[int]:
    """Extract year from date string."""
    if pd.isna(date_str):
        return None
    try:
        return pd.to_datetime(date_str, errors='coerce').year
    except:
        return None

def normalize_name(name: str) -> str:
    """Normalize names for better matching by handling initials and middle names."""
    if pd.isna(name):
        return ""
    
    name = str(name).lower().strip()
    # Remove punctuation
    name = re.sub(r'[.,]', '', name)
    # Split into parts
    parts = name.split()
    
    if len(parts) <= 2:
        return name
    
    # Handle middle name/initial: Keep first and last, convert middle to initial
    first = parts[0]
    last = parts[-1]
    middle_parts = parts[1:-1]
    
    # Convert middle names to initials
    middle_initials = [p[0] if len(p) > 0 else '' for p in middle_parts]
    
    # Create normalized version with initials
    normalized = f"{first} {' '.join(middle_initials)} {last}"
    
    return normalized.strip()

def calculate_match_score(source_person, target_person, weights=None) -> Tuple[float, dict]:
    """
    Calculate a weighted match score between two individuals.
    Returns (total_score, details_dict)
    
    Scoring system:
    - Name similarity: 0-40 points
    - Birth date match: 0-25 points
    - Death date match: 0-25 points
    - Parent names match: 0-10 points
    
    Total possible: 100 points
    """
    if weights is None:
        weights = {
            'name': 40,
            'birth': 25,
            'death': 25,
            'parents': 10
        }
    
    from thefuzz import fuzz
    details = {}
    score = 0
    
    # 1. NAME MATCHING (0-40 points)
    sp_name = str(source_person.get('Full Name', '')).lower().strip()
    tp_name = str(target_person.get('Full Name', '')).lower().strip()
    
    if sp_name and tp_name:
        # Try multiple matching strategies
        direct_score = fuzz.ratio(sp_name, tp_name)
        token_sort_score = fuzz.token_sort_ratio(sp_name, tp_name)
        
        # Normalized with initials
        norm_sp = normalize_name(sp_name)
        norm_tp = normalize_name(tp_name)
        normalized_score = fuzz.ratio(norm_sp, norm_tp)
        
        # Use best score
        best_name_score = max(direct_score, token_sort_score, normalized_score)
        name_points = (best_name_score / 100) * weights['name']
        score += name_points
        details['name_score'] = best_name_score
        details['name_points'] = name_points
    else:
        details['name_score'] = 0
        details['name_points'] = 0
    
    # 2. BIRTH DATE MATCHING (0-25 points)
    sp_birth = source_person.get('Birth Date')
    tp_birth = target_person.get('Birth Date')
    
    if pd.notna(sp_birth) and pd.notna(tp_birth):
        sp_birth_year = get_year(sp_birth)
        tp_birth_year = get_year(tp_birth)
        
        if sp_birth_year and tp_birth_year:
            year_diff = abs(sp_birth_year - tp_birth_year)
            if year_diff == 0:
                birth_points = weights['birth']  # Perfect match
            elif year_diff == 1:
                birth_points = weights['birth'] * 0.8  # 1 year off
            elif year_diff == 2:
                birth_points = weights['birth'] * 0.6  # 2 years off
            elif year_diff <= 5:
                birth_points = weights['birth'] * 0.3  # Close
            else:
                birth_points = 0
            
            score += birth_points
            details['birth_diff'] = year_diff
            details['birth_points'] = birth_points
        else:
            details['birth_diff'] = None
            details['birth_points'] = 0
    else:
        details['birth_diff'] = None
        details['birth_points'] = 0
    
    # 3. DEATH DATE MATCHING (0-25 points)
    sp_death = source_person.get('Death Date')
    tp_death = target_person.get('Death Date')
    
    if pd.notna(sp_death) and pd.notna(tp_death):
        sp_death_year = get_year(sp_death)
        tp_death_year = get_year(tp_death)
        
        if sp_death_year and tp_death_year:
            year_diff = abs(sp_death_year - tp_death_year)
            if year_diff == 0:
                death_points = weights['death']  # Perfect match
            elif year_diff == 1:
                death_points = weights['death'] * 0.8  # 1 year off
            elif year_diff == 2:
                death_points = weights['death'] * 0.6  # 2 years off
            elif year_diff <= 5:
                death_points = weights['death'] * 0.3  # Close
            else:
                death_points = 0
            
            score += death_points
            details['death_diff'] = year_diff
            details['death_points'] = death_points
        else:
            details['death_diff'] = None
            details['death_points'] = 0
    else:
        details['death_diff'] = None
        details['death_points'] = 0
    
    # 4. PARENT NAME MATCHING (0-10 points)
    parent_points = 0
    
    # Father
    sp_father = str(source_person.get("Father's Full Name", '')).lower().strip()
    tp_father = str(target_person.get("Father's Full Name", '')).lower().strip()
    if sp_father and tp_father and sp_father != 'nan' and tp_father != 'nan':
        father_score = fuzz.token_sort_ratio(sp_father, tp_father)
        if father_score >= 80:
            parent_points += weights['parents'] * 0.5
    
    # Mother
    sp_mother = str(source_person.get("Mother's Full Name", '')).lower().strip()
    tp_mother = str(target_person.get("Mother's Full Name", '')).lower().strip()
    if sp_mother and tp_mother and sp_mother != 'nan' and tp_mother != 'nan':
        mother_score = fuzz.token_sort_ratio(sp_mother, tp_mother)
        if mother_score >= 80:
            parent_points += weights['parents'] * 0.5
    
    score += parent_points
    details['parent_points'] = parent_points
    details['total_score'] = score
    
    return score, details

# ==============================================================================
# SECTION 2: REUSABLE UI AND MAIN LAYOUT
# ==============================================================================

def create_processor_ui(title: str, upload_label: str, button_label: str, 
                       session_df_key: str, session_name_key: str, uploader_key: str):
    """Creates a UI for processing either a GEDCOM or a CSV file."""
    with st.expander(title, expanded=True):
        uploaded_file = st.file_uploader(upload_label, type=["ged", "txt", "csv"], key=uploader_key)
        
        if uploaded_file:
            dataset = None
            
            if uploaded_file.name.lower().endswith('.csv'):
                with st.spinner("Loading CSV..."):
                    dataset = pd.read_csv(uploaded_file)
                st.info(f"📊 Loaded {len(dataset)} rows from CSV: **{uploaded_file.name}**")
            else:
                with st.spinner("Parsing GEDCOM..."):
                    try:
                        contents = uploaded_file.read().decode("utf-8-sig")
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        contents = uploaded_file.read().decode("latin-1")
                    
                    individuals, families = parse_gedcom(contents)
                    if individuals:
                        dataset = generate_individual_dataset(individuals, families)
                        st.info(f"👥 Parsed {len(dataset)} individuals from GEDCOM: **{uploaded_file.name}**")
                    else:
                        st.warning("⚠️ No individuals found in this GEDCOM file.")
            
            if dataset is not None:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button(button_label, use_container_width=True, key=f"{uploader_key}_button"):
                        st.session_state[session_df_key] = dataset
                        st.session_state[session_name_key] = uploaded_file.name
                        st.success(f"✅ Set as {session_df_key.split('_')[0].upper()}")
                        st.rerun()
                
                with col2:
                    # Quick stats
                    birth_count = dataset['Birth Date'].notna().sum()
                    death_count = dataset['Death Date'].notna().sum()
                    st.caption(f"📅 Birth dates: {birth_count} | Death dates: {death_count}")
                
                with st.container():
                    st.dataframe(dataset, use_container_width=True, height=250)

# --- Initialize session state ---
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None

# --- Main Page Layout ---
st.title("🌳 Genealogy Workbench")
st.caption("v2026.1 by Ken Harmon | A unified tool for genealogy file processing and comparison")
st.markdown("---")

# --- Render UI Components ---
create_processor_ui(
    title="📥 STEP 1: Process Source File (Ancestry/GEDCOM/CSV)",
    upload_label="Upload Source File",
    button_label="Set as SOURCE",
    session_df_key='source_df',
    session_name_key='source_name',
    uploader_key='anc_uploader'
)

create_processor_ui(
    title="📥 STEP 2: Process Target File (FamilySearch/GEDCOM/CSV)",
    upload_label="Upload Target File",
    button_label="Set as TARGET",
    session_df_key='target_df',
    session_name_key='target_name',
    uploader_key='fs_uploader'
)

# ==============================================================================
# SECTION 3: COMPARISON ENGINE
# ==============================================================================

with st.expander("🔍 STEP 3: Compare Source and Target", expanded=True):
    st.subheader("AI-Assisted Genealogy Comparison")
    st.write("Find individuals from Source who are likely missing in Target using semantic matching.")

    col1, col2 = st.columns(2)
    source_ready = 'source_df' in st.session_state and st.session_state.source_df is not None
    target_ready = 'target_df' in st.session_state and st.session_state.target_df is not None
    
    with col1:
        if source_ready:
            st.success(f"✅ SOURCE: **{st.session_state.source_name}** ({len(st.session_state.source_df)} records)")
        else:
            st.warning("⚠️ SOURCE NOT LOADED")
    
    with col2:
        if target_ready:
            st.success(f"✅ TARGET: **{st.session_state.target_name}** ({len(st.session_state.target_df)} records)")
        else:
            st.warning("⚠️ TARGET NOT LOADED")
    
    st.markdown("---")

    if source_ready and target_ready:
        # Matching settings in columns for better layout
        col1, col2 = st.columns(2)
        with col1:
            match_threshold = st.slider("Match Threshold Score", 50, 95, 70, 
                                      help="Minimum total score (out of 100) to consider a match. Lower = more lenient.")
        with col2:
            st.info("""
            **Scoring System:**
            - Name: 40 pts
            - Birth Date: 25 pts
            - Death Date: 25 pts
            - Parents: 10 pts
            """)

        if st.button("🚀 Run Comparison", use_container_width=True, type="primary"):
            source_df = st.session_state.source_df.copy()
            target_df = st.session_state.target_df.copy()
            
            total_comparisons = len(source_df) * len(target_df)
            st.info(f"Processing {len(source_df)} source records against {len(target_df)} target records...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            # PRE-PROCESSING: Index target by birth year for fast lookup
            target_by_year = {}
            for tidx, tperson in target_df.iterrows():
                birth_year = get_year(tperson.get('Birth Date'))
                if birth_year:
                    if birth_year not in target_by_year:
                        target_by_year[birth_year] = []
                    target_by_year[birth_year].append(tidx)
            
            # Also keep track of records without birth dates
            target_no_birth = []
            for tidx, tperson in target_df.iterrows():
                if not get_year(tperson.get('Birth Date')):
                    target_no_birth.append(tidx)

            missing_indices = []
            match_details = []
            
            comparisons_made = 0
            comparisons_skipped = 0

            # Process each source person
            for idx, source_person in source_df.iterrows():
                # Update progress
                progress = idx / len(source_df)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx + 1} of {len(source_df)}: {source_person['Full Name']}")
                
                best_score = 0
                best_match_idx = None
                best_details = None
                
                # SMART FILTERING: Only compare against candidates with similar birth years
                sp_birth_year = get_year(source_person.get('Birth Date'))
                candidate_indices = []
                
                if sp_birth_year:
                    # Look for matches within ±5 years
                    year_range = 5
                    for year in range(sp_birth_year - year_range, sp_birth_year + year_range + 1):
                        if year in target_by_year:
                            candidate_indices.extend(target_by_year[year])
                    # Also check records without birth dates
                    candidate_indices.extend(target_no_birth)
                else:
                    # No birth year in source - must check all targets
                    candidate_indices = list(range(len(target_df)))
                
                comparisons_skipped += len(target_df) - len(candidate_indices)
                
                # Compare only against filtered candidates
                for tidx in candidate_indices:
                    target_person = target_df.iloc[tidx]
                    score, details = calculate_match_score(source_person, target_person)
                    comparisons_made += 1
                    
                    if score > best_score:
                        best_score = score
                        best_match_idx = tidx
                        best_details = details
                    
                    # Early exit if perfect match found
                    if score >= 95:
                        break
                
                # Determine if this is a match
                if best_score < match_threshold:
                    missing_indices.append(idx)
                    
                    match_info = {
                        'index': idx,
                        'name': source_person['Full Name'],
                        'birth': source_person.get('Birth Date'),
                        'death': source_person.get('Death Date'),
                        'best_match': target_df.iloc[best_match_idx]['Full Name'] if best_match_idx is not None else None,
                        'match_birth': target_df.iloc[best_match_idx].get('Birth Date') if best_match_idx is not None else None,
                        'match_death': target_df.iloc[best_match_idx].get('Death Date') if best_match_idx is not None else None,
                        'score': round(best_score, 1),
                        'name_similarity': round(best_details.get('name_score', 0), 1) if best_details else 0,
                        'birth_diff': best_details.get('birth_diff') if best_details else None,
                        'death_diff': best_details.get('death_diff') if best_details else None,
                        'reason': 'No strong match found'
                    }
                    match_details.append(match_info)
            
            progress_bar.progress(1.0)
            efficiency = (comparisons_skipped / total_comparisons * 100) if total_comparisons > 0 else 0
            status_text.text(f"✅ Complete! Made {comparisons_made:,} comparisons (skipped {comparisons_skipped:,} - {efficiency:.1f}% reduction)")
            
            # Store results
            st.session_state.comparison_results = {
                'missing_indices': missing_indices,
                'match_details': match_details,
                'source_df': source_df
            }

            st.success(f"✅ Found **{len(missing_indices)}** likely missing individuals out of {len(source_df)} source records.")
            
            # Clear progress indicators after a moment
            import time
            time.sleep(2)
            progress_bar.empty()
            status_text.empty()

        # Display results
        if st.session_state.comparison_results:
            results = st.session_state.comparison_results
            missing_indices = results['missing_indices']
            
            if missing_indices:
                missing_df = results['source_df'].loc[missing_indices].copy()
                
                # Add match details
                if results['match_details']:
                    match_info = pd.DataFrame(results['match_details'])
                    
                    # Create display columns
                    display_cols = ['name', 'birth', 'death', 'score', 'name_similarity', 
                                   'best_match', 'match_birth', 'match_death', 'birth_diff', 'death_diff']
                    
                    match_display = match_info[display_cols].copy()
                    match_display.columns = ['Source Name', 'Source Birth', 'Source Death', 
                                            'Match Score', 'Name %', 'Best Match Name', 
                                            'Match Birth', 'Match Death', 'Birth Δ Years', 'Death Δ Years']
                    
                    st.subheader("Missing Individuals with Best Matches")
                    st.dataframe(match_display, use_container_width=True, height=400)
                    
                    # Show score distribution
                    st.subheader("Score Analysis")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_score = match_info['score'].mean()
                        st.metric("Average Match Score", f"{avg_score:.1f}/100")
                    with col2:
                        high_scores = len(match_info[match_info['score'] >= 60])
                        st.metric("Close Calls (60-70 score)", high_scores)
                    with col3:
                        low_scores = len(match_info[match_info['score'] < 40])
                        st.metric("Very Different (<40 score)", low_scores)
                
                col1, col2 = st.columns(2)
                with col1:
                    # Export for further review
                    export_df = match_display.copy()
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "⬇️ Download Missing Persons CSV",
                        csv,
                        f"missing_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Excel download option
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='Missing Persons')
                    
                    st.download_button(
                        "⬇️ Download as Excel",
                        buffer.getvalue(),
                        f"missing_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("🎉 No missing individuals found! All source records appear to have matches in the target.")
    else:
        st.info("ℹ️ Please load both Source and Target datasets above to enable comparison.")

# --- Sidebar Info ---
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    **Genealogy Workbench** helps you:
    - Parse GEDCOM files from Ancestry/FamilySearch
    - Import genealogy data from CSV files
    - Compare datasets to find missing individuals
    - Export results for further research
    
    **Tips:**
    - Start by uploading your source file (Step 1)
    - Then upload your target file (Step 2)
    - Adjust matching settings as needed
    - Use fuzzy matching for faster results
    """)
    
    st.markdown("---")
    st.caption("Built with Streamlit • v2026.1")