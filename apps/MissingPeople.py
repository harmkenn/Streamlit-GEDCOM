import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder
from fuzzywuzzy import fuzz
from datetime import datetime

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="Enhanced GEDCOM Comparison Tool v1.2")

def parse_date(date_str):
    """
    Parses a GEDCOM date string into a datetime object.
    Returns None if the date cannot be parsed.
    """
    try:
        return datetime.strptime(date_str, "%d %b %Y")
    except ValueError:
        return None

def parse_gedcom(file_contents):
    """
    Parses a GEDCOM file and extracts individuals and their data.
    """
    individuals = {}
    current_individual = None
    current_individual_data = {}
    current_tag = None

    for line in file_contents.splitlines():
        line = line.strip()
        if line.startswith('0 @I'):  # Start of a new individual
            if current_individual is not None:
                individuals[current_individual] = current_individual_data
                current_individual_data = {}
            current_individual = line.split('@')[1]
        elif line.startswith('1'):  # Level 1 tags
            parts = line.split(' ')
            current_tag = parts[1]
            value = parts[2:]
            current_individual_data.setdefault(current_tag, []).append(' '.join(value))
        elif line.startswith('2'):  # Level 2 tags
            parts = line.split(' ')
            add_tag = parts[1]
            value = parts[2:]
            full_tag = current_tag + add_tag
            current_individual_data.setdefault(full_tag, []).append(' '.join(value))
        else:
            continue

    if current_individual is not None:
        individuals[current_individual] = current_individual_data

    return individuals

@st.cache_data
def convert_df_to_excel(df):
    """
    Converts a DataFrame to an Excel file for download.
    """
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

def compare_individuals(ancestry_individuals, familysearch_individuals):
    """
    Compares individuals from two GEDCOM files based on names, dates, and relationships.
    """
    missing_individuals = []

    for ancestry_id, ancestry_individual in ancestry_individuals.items():
        ancestry_name = ' '.join(ancestry_individual.get('NAME', ['Unknown']))
        ancestry_birth_date = parse_date(ancestry_individual.get('BIRTDATE', ['Unknown'])[0])
        ancestry_death_date = parse_date(ancestry_individual.get('DEATDATE', ['Unknown'])[0])
        ancestry_parents = ancestry_individual.get('FAMC', [])
        ancestry_children = ancestry_individual.get('FAMS', [])
        ancestry_spouses = ancestry_individual.get('FAMS', [])

        match_found = False

        for familysearch_id, familysearch_individual in familysearch_individuals.items():
            familysearch_name = ' '.join(familysearch_individual.get('NAME', ['Unknown']))
            familysearch_birth_date = parse_date(familysearch_individual.get('BIRTDATE', ['Unknown'])[0])
            familysearch_death_date = parse_date(familysearch_individual.get('DEATDATE', ['Unknown'])[0])
            familysearch_parents = familysearch_individual.get('FAMC', [])
            familysearch_children = familysearch_individual.get('FAMS', [])
            familysearch_spouses = familysearch_individual.get('FAMS', [])

            # Fuzzy name matching
            name_similarity = fuzz.ratio(ancestry_name, familysearch_name)

            # Date matching with tolerance
            birth_date_match = (
                ancestry_birth_date and familysearch_birth_date and
                abs((ancestry_birth_date - familysearch_birth_date).days) <= 365
            )
            death_date_match = (
                ancestry_death_date and familysearch_death_date and
                abs((ancestry_death_date - familysearch_death_date).days) <= 365
            )

            # Relationship matching
            parents_match = set(ancestry_parents) & set(familysearch_parents)
            children_match = set(ancestry_children) & set(familysearch_children)
            spouses_match = set(ancestry_spouses) & set(familysearch_spouses)

            # Define match criteria
            if name_similarity >= 80 and (birth_date_match or death_date_match) and (parents_match or children_match or spouses_match):
                match_found = True
                break

        if not match_found:
            missing_individuals.append({
                'ID': ancestry_id,
                'NAME': ancestry_name,
                'BIRTHDATE': ancestry_birth_date.strftime("%d %b %Y") if ancestry_birth_date else 'Unknown',
                'DEATHDATE': ancestry_death_date.strftime("%d %b %Y") if ancestry_death_date else 'Unknown',
                'PARENTS': ', '.join(ancestry_parents),
                'CHILDREN': ', '.join(ancestry_children),
                'SPOUSES': ', '.join(ancestry_spouses)
            })

    return pd.DataFrame(missing_individuals)

def main():
    st.title("Enhanced GEDCOM Comparison Tool")
    st.sidebar.write("Upload two GEDCOM files to compare individuals")

    # File upload for FamilySearch GEDCOM
    familysearch_file = st.sidebar.file_uploader("Upload FamilySearch GEDCOM", type=["ged"])
    ancestry_file = st.sidebar.file_uploader("Upload Ancestry GEDCOM", type=["ged"])

    if familysearch_file and ancestry_file:
        try:
            # Read the uploaded files
            familysearch_contents = familysearch_file.read().decode('utf-8')
            ancestry_contents = ancestry_file.read().decode('utf-8')

            if st.sidebar.button("Compare GEDCOMs"):
                # Parse both GEDCOM files
                familysearch_individuals = parse_gedcom(familysearch_contents)
                ancestry_individuals = parse_gedcom(ancestry_contents)

                # Compare individuals
                missing_individuals_df = compare_individuals(ancestry_individuals, familysearch_individuals)

                # Display results
                st.subheader("Individuals Missing from FamilySearch GEDCOM")
                if missing_individuals_df.empty:
                    st.write("No missing individuals found.")
                else:
                    st.write(f"Found {len(missing_individuals_df)} individuals missing from FamilySearch GEDCOM.")
                    gb = GridOptionsBuilder.from_dataframe(missing_individuals_df)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)
                    gridOptions = gb.build()

                    AgGrid(missing_individuals_df, gridOptions=gridOptions)

                    # Download button for missing individuals
                    st.download_button(
                        label="Export Missing Individuals to Excel",
                        data=convert_df_to_excel(missing_individuals_df),
                        file_name="missing_individuals.xlsx",
                        mime="application/vnd.ms-excel",
                    )

        except Exception as e:
            st.error(f"Error processing GEDCOM files: {e}")

if __name__ == "__main__":
    main()
