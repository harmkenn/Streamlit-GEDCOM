# v1.0
import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder
from graphviz import Digraph

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="Gedcoms")

def parse_gedcom(file_contents):
    individuals = {}
    current_individual = None
    current_individual_data = {}
    current_tag = None

    for line in file_contents.splitlines():
        line = line.strip()
        if line.startswith('0 @I'):
            if current_individual is not None:
                individuals[current_individual] = current_individual_data
                current_individual_data = {}
            current_individual = line.split('@')[1]
        elif line.startswith('1'):
            parts = line.split(' ')
            current_tag = parts[1]
            value = parts[2:]
            current_individual_data.setdefault(current_tag, []).append(' '.join(value))
        elif line.startswith('2'):
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
def convert_df(df):
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

def visualize_family_tree(individuals):
    dot = Digraph()

    # Add nodes for individuals
    for individual_id, individual in individuals.items():
        name = ' '.join(individual.get('NAME', ['Unknown']))
        dot.node(individual_id, name)

    # Add edges for relationships
    for individual_id, individual in individuals.items():
        for fam in individual.get('FAMS', []):
            dot.edge(individual_id, fam, label="Parent")

    return dot

def main():
    st.title("Gedcom from Ancestry v1.0")
    st.sidebar.write("Upload a Gedcom file to parse its contents")

    uploaded_file = st.sidebar.file_uploader("Choose a Gedcom file", type="ged")

    if uploaded_file is not None:
        try:
            file_contents = uploaded_file.read().decode('utf-8')

            if st.sidebar.button("Submit"):
                individuals = parse_gedcom(file_contents)
                individual_data = []
                max_fams_count = 0

                # First pass to find the max number of FAMS entries
                for individual in individuals.values():
                    fams_count = len(individual.get('FAMS', []))
                    if fams_count > max_fams_count:
                        max_fams_count = fams_count

                for individual_id, individual in individuals.items():
                    data = {'ID': individual_id}
                    for tag, values in individual.items():
                        if tag == 'FAMS':
                            for i, fam in enumerate(values):
                                data[f'FAMS_{i+1}'] = fam
                        else:
                            data[tag] = ' '.join(values)
                    individual_data.append(data)

                individual_df = pd.DataFrame(individual_data)

                # Build the list of expected columns
                fams_columns = [f'FAMS_{i+1}' for i in range(max_fams_count)]
                columns_to_keep = ['ID', 'NAME', '_FSFTID', 'SEX', 'BIRTDATE', 'BIRTDATEPLAC', 'FAMC', 'DEAT',
                                   'DEATDATE', 'DEATDATEPLAC', 'BAPLDATE', 'BAPLDATETEMP', 'CONLDATE', 'CONLDATETEMP',
                                   'ENDLDATE', 'ENDLDATETEMP', 'BURIDATE', 'BURIDATEPLAC', 'BURIPLAC'] + fams_columns

                individual_df = individual_df.reindex(columns=columns_to_keep)

                # Extract birth and death years
                individual_df.insert(3, 'BIRTHYEAR', individual_df['BIRTDATE'].str.extract(r'(\d{4})$'))
                individual_df.insert(10, 'DEATHYEAR', individual_df['DEATDATE'].str.extract(r'(\d{4})$'))
                individual_df['BIRTHYEAR'] = pd.to_numeric(individual_df['BIRTHYEAR'], errors='coerce')
                individual_df['DEATHYEAR'] = pd.to_numeric(individual_df['DEATHYEAR'], errors='coerce')

                # Compute AGE
                mask = individual_df['DEATHYEAR'].notnull() & individual_df['BIRTHYEAR'].notnull()
                individual_df.loc[mask, 'AGE'] = individual_df.loc[mask, 'DEATHYEAR'] - individual_df.loc[mask, 'BIRTHYEAR']

                # Count CHILDREN using FAMC appearances
                famc_counts = individual_df['FAMC'].value_counts()
                individual_df['CHILDREN'] = individual_df[fams_columns].apply(
                    lambda row: sum(famc_counts.get(fam, 0) for fam in row if pd.notna(fam)),
                    axis=1
                )

                # Save in session state
                st.session_state.individual_df = individual_df

                # Display grid
                st.write("Parsed Individuals:")
                gb = GridOptionsBuilder.from_dataframe(individual_df)
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)
                gridOptions = gb.build()

                AgGrid(individual_df, gridOptions=gridOptions)

                # Download button
                st.download_button(
                    label="Export to Excel",
                    data=convert_df(individual_df),
                    file_name="individuals.xlsx",
                    mime="application/vnd.ms-excel",
                )

                # Family Tree Visualization
                st.subheader("Family Tree Visualization")
                dot = visualize_family_tree(individuals)
                st.graphviz_chart(dot)

                # Search Functionality
                st.subheader("Search Individuals")
                search_query = st.text_input("Search for an individual by name or ID:")
                if search_query:
                    filtered_df = individual_df[individual_df['NAME'].str.contains(search_query, na=False)]
                    st.write(filtered_df)

                # Filter by Birth Year
                st.subheader("Filter by Birth Year")
                birth_year_filter = st.slider("Filter by Birth Year", min_value=1800, max_value=2023, value=(1900, 2000))
                filtered_df = individual_df[
                    (individual_df['BIRTHYEAR'] >= birth_year_filter[0]) &
                    (individual_df['BIRTHYEAR'] <= birth_year_filter[1])
                ]
                st.write(filtered_df)

        except Exception as e:
            st.error(f"Error parsing GEDCOM file: {e}")

if __name__ == "__main__":
    main()
