import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Comparison Tool")

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

def main():
    st.title("GEDCOM Comparison Tool")
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

                # Convert parsed data into DataFrames
                familysearch_data = []
                ancestry_data = []

                for individual_id, individual in familysearch_individuals.items():
                    data = {'ID': individual_id, 'NAME': ' '.join(individual.get('NAME', ['Unknown']))}
                    familysearch_data.append(data)

                for individual_id, individual in ancestry_individuals.items():
                    data = {'ID': individual_id, 'NAME': ' '.join(individual.get('NAME', ['Unknown']))}
                    ancestry_data.append(data)

                familysearch_df = pd.DataFrame(familysearch_data)
                ancestry_df = pd.DataFrame(ancestry_data)

                # Find missing individuals
                missing_individuals = ancestry_df[~ancestry_df['NAME'].isin(familysearch_df['NAME'])]

                # Display results
                st.subheader("Individuals Missing from FamilySearch GEDCOM")
                if missing_individuals.empty:
                    st.write("No missing individuals found.")
                else:
                    st.write(f"Found {len(missing_individuals)} individuals missing from FamilySearch GEDCOM.")
                    gb = GridOptionsBuilder.from_dataframe(missing_individuals)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)
                    gridOptions = gb.build()

                    AgGrid(missing_individuals, gridOptions=gridOptions)

                    # Download button for missing individuals
                    st.download_button(
                        label="Export Missing Individuals to Excel",
                        data=convert_df_to_excel(missing_individuals),
                        file_name="missing_individuals.xlsx",
                        mime="application/vnd.ms-excel",
                    )

        except Exception as e:
            st.error(f"Error processing GEDCOM files: {e}")

if __name__ == "__main__":
    main()
