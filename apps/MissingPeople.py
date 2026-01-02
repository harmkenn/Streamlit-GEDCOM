import streamlit as st
import pandas as pd
from thefuzz import fuzz # For fuzzy string matching
from typing import Optional, Any

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Genealogy Comparator")

# --- Helper Functions ---

def get_year(date_str: Any) -> Optional[int]:
    """Safely extracts the year from a date string."""
    if pd.isna(date_str) or not isinstance(date_str, str):
        return None
    try:
        # Extract the first 4-digit number as the year
        year_match = pd.to_datetime(date_str, errors='coerce')
        if pd.notna(year_match):
            return year_match.year
    except Exception:
        return None
    return None

# --- Main Application UI ---
st.title("🔬 Genealogy CSV Comparator")
st.write(
    "Upload two genealogy CSV files to find people who exist in the "
    "first file (Source) but are missing from the second (Target)."
)

# --- Matching Configuration in Sidebar ---
st.sidebar.header("⚙️ Matching Settings")

name_threshold = st.sidebar.slider(
    "Name Similarity Threshold (%)",
    min_value=50,
    max_value=100,
    value=85,
    help="How similar do names need to be to be considered a match? 100 is an exact match."
)

year_tolerance = st.sidebar.slider(
    "Year Tolerance (+/-)",
    min_value=0,
    max_value=10,
    value=1,
    help="How many years of difference are allowed for birth/death dates?"
)

st.sidebar.write("---")

# --- File Uploaders ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Source File")
    source_file = st.file_uploader(
        "Upload the main CSV (e.g., Ancestry)",
        type="csv",
        key="source"
    )

with col2:
    st.subheader("Target File")
    target_file = st.file_uploader(
        "Upload the CSV to check against (e.g., FamilySearch)",
        type="csv",
        key="target"
    )


# --- Main Comparison Logic ---
if st.button("🚀 Run Comparison", use_container_width=True) and source_file and target_file:
    with st.spinner("Loading and preparing data..."):
        # Load data into pandas DataFrames
        source_df = pd.read_csv(source_file)
        target_df = pd.read_csv(target_file)

        # Pre-process data for faster comparison
        # Convert names to lowercase and extract years
        source_df['clean_name'] = source_df['Full Name'].str.lower().str.strip()
        source_df['birth_year'] = source_df['Birth Date'].apply(get_year)
        source_df['death_year'] = source_df['Death Date'].apply(get_year)
        source_df['clean_father'] = source_df["Father's Full Name"].str.lower().str.strip()
        source_df['clean_mother'] = source_df["Mother's Full Name"].str.lower().str.strip()
        
        target_df['clean_name'] = target_df['Full Name'].str.lower().str.strip()
        target_df['birth_year'] = target_df['Birth Date'].apply(get_year)
        target_df['death_year'] = target_df['Death Date'].apply(get_year)
        target_df['clean_father'] = target_df["Father's Full Name"].str.lower().str.strip()
        target_df['clean_mother'] = target_df["Mother's Full Name"].str.lower().str.strip()
        
    with st.spinner("Comparing records... This might take a moment."):
        missing_people_rows = []
        total_source_rows = len(source_df)

        # Loop through each person in the source file
        for index, source_person in source_df.iterrows():
            found_match = False
            
            # Now, search for a match in the entire target file
            for _, target_person in target_df.iterrows():
                
                # 1. Check Name Similarity
                name_similarity = fuzz.ratio(source_person['clean_name'], target_person['clean_name'])
                if name_similarity < name_threshold:
                    continue # Not a match, try next person

                # 2. Check Birth Year Tolerance
                if source_person['birth_year'] and target_person['birth_year']:
                    if abs(source_person['birth_year'] - target_person['birth_year']) > year_tolerance:
                        continue # Birth years are too far apart

                # 3. Check Death Year Tolerance
                if source_person['death_year'] and target_person['death_year']:
                    if abs(source_person['death_year'] - target_person['death_year']) > year_tolerance:
                        continue # Death years are too far apart
                
                # 4. Check Parent Name Similarity
                father_similarity = fuzz.ratio(str(source_person['clean_father']), str(target_person['clean_father']))
                mother_similarity = fuzz.ratio(str(source_person['clean_mother']), str(target_person['clean_mother']))
                
                # We can be more lenient with parents
                if father_similarity < name_threshold - 10 or mother_similarity < name_threshold - 10:
                    continue

                # If all checks passed, we found a match!
                found_match = True
                break # Stop searching for this person and move to the next in the source file
            
            # If after checking all target people, no match was found...
            if not found_match:
                missing_people_rows.append(source_person)

    st.success(f"Comparison complete! Found **{len(missing_people_rows)}** people in the source file who are likely missing from the target file.")

    if missing_people_rows:
        # Create a DataFrame from the missing people
        missing_df = pd.DataFrame(missing_people_rows)
        # Drop the temporary 'clean' columns before displaying
        columns_to_show = [col for col in source_df.columns if not col.startswith('clean_')]
        st.dataframe(missing_df[columns_to_show], use_container_width=True)

        # Allow downloading the results
        csv_data = missing_df[columns_to_show].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Missing Persons as CSV",
            data=csv_data,
            file_name="missing_persons.csv",
            mime="text/csv",
        )
