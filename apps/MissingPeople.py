import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder
from fuzzywuzzy import fuzz
from datetime import datetime

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="Enhanced GEDCOM Comparison Tool v1.3")

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
    Builds relationships between individuals.
    """
    individuals = {}
    relationships = {"parents": {}, "children": {}, "spouses": {}}
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
        elif line.startswith('1 FAMC'):  # Parent-child relationship
            parent_id = line.split('@')[1]
            relationships["children"].setdefault(parent_id, []).append(current_individual)
            relationships["parents"].setdefault(current_individual, []).append(parent_id)
        elif line.startswith('1 FAMS'):  # Spouse relationship
            spouse_id = line.split('@')[1]
            relationships["spouses"].setdefault(current_individual, []).append(spouse_id)
            relationships["spouses"].setdefault(spouse_id, []).append(current_individual)
        else:
            continue

    if current_individual is not None:
        individuals[current_individual] = current_individual_data

    return individuals, relationships

def find_descendants(individual_id, relationships, individuals, descendants=None):
    """
    Recursively finds all descendants of a given individual.
    """
    if descendants is None:
        descendants = []

    children = relationships["children"].get(individual_id, [])
    for child_id in children:
        if child_id not in descendants:
            descendants.append(child_id)
            find_descendants(child_id, relationships, individuals, descendants)

    return descendants

@st.cache_data
def convert_df_to_excel(df):
    """
    Converts a DataFrame to an Excel file for download.
    """
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

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

            # Parse both GEDCOM files
            familysearch_individuals, familysearch_relationships = parse_gedcom(familysearch_contents)
            ancestry_individuals, ancestry_relationships = parse_gedcom(ancestry_contents)

            # Select ancestor for filtering
            st.sidebar.subheader("Filter by Ancestor")
            ancestor_id = st.sidebar.selectbox(
                "Select an ancestor from FamilySearch GEDCOM",
                options=list(familysearch_individuals.keys()),
                format_func=lambda x: ' '.join(familysearch_individuals[x].get('NAME', ['Unknown']))
            )

            if ancestor_id:
                # Find descendants and their spouses
                descendants = find_descendants(ancestor_id, familysearch_relationships, familysearch_individuals)
                descendants_data = []

                for descendant_id in descendants:
                    descendant = familysearch_individuals[descendant_id]
                    descendant_name = ' '.join(descendant.get('NAME', ['Unknown']))
                    descendant_birth_date = parse_date(descendant.get('BIRTDATE', ['Unknown'])[0])
                    descendant_death_date = parse_date(descendant.get('DEATDATE', ['Unknown'])[0])
                    descendant_spouses = familysearch_relationships["spouses"].get(descendant_id, [])

                    descendants_data.append({
                        'ID': descendant_id,
                        'NAME': descendant_name,
                        'BIRTHDATE': descendant_birth_date.strftime("%d %b %Y") if descendant_birth_date else 'Unknown',
                        'DEATHDATE': descendant_death_date.strftime("%d %b %Y") if descendant_death_date else 'Unknown',
                        'SPOUSES': ', '.join([
                            ' '.join(familysearch_individuals[spouse_id].get('NAME', ['Unknown']))
                            for spouse_id in descendant_spouses
                        ])
                    })

                descendants_df = pd.DataFrame(descendants_data)

                # Display results
                st.subheader(f"Descendants of {ancestor_id}")
                if descendants_df.empty:
                    st.write("No descendants found.")
                else:
                    st.write(f"Found {len(descendants_df)} descendants.")
                    gb = GridOptionsBuilder.from_dataframe(descendants_df)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)
                    gridOptions = gb.build()

                    AgGrid(descendants_df, gridOptions=gridOptions)

                    # Download button for descendants
                    st.download_button(
                        label="Export Descendants to Excel",
                        data=convert_df_to_excel(descendants_df),
                        file_name="descendants.xlsx",
                        mime="application/vnd.ms-excel",
                    )

        except Exception as e:
            st.error(f"Error processing GEDCOM files: {e}")

if __name__ == "__main__":
    main()
