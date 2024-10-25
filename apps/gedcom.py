import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder

# Set the page layout to wide
st.set_page_config(layout="wide", page_title=f"Gedcoms")

def parse_gedcom(file_contents):
    individuals = {}
    current_individual = None
    current_individual_data = {}

    for line in file_contents.splitlines():
        line = line.strip()
        if line.startswith('0 @I'):
            if current_individual is not None:
                individuals[current_individual] = current_individual_data
                current_individual_data = {}
            current_individual = line.split('@')[1]
        elif line.startswith('1'):
            current_tag = line.split(' ')[1]
            value = line.split(' ')[2:]
            current_individual_data[current_tag] = value
        elif line.startswith('2'):
            add_tag = line.split(' ')[1]
            current_tag = current_tag + add_tag
            value = line.split(' ')[2:]
            current_individual_data[current_tag] = value
        else:
            continue

    if current_individual is not None:
        individuals[current_individual] = current_individual_data

    return individuals

def main():
    st.title("Gedcom to Excel v1.0")
    st.sidebar.write("Upload a Gedcom file to parse its contents")

    uploaded_file = st.sidebar.file_uploader("Choose a Gedcom file", type="ged")

    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode('utf-8')

    if st.sidebar.button("Submit"):
        if uploaded_file is not None:
            individuals = parse_gedcom(file_contents)
            individual_data = []
            for individual_id, individual in individuals.items():
                data = {'ID': individual_id}
                for tag, values in individual.items():
                    data[tag] = ' '.join(values)
                individual_data.append(data)

            individual_df = pd.DataFrame(individual_data)
            st.write("Parsed Data:")
            #st.dataframe(individual_df, use_container_width=True)

            # Store the DataFrame in session state
            st.session_state.individual_df = individual_df

            # Create a GridOptionsBuilder object
            gb = GridOptionsBuilder.from_dataframe(individual_df)
            gb.configure_pagination(paginationAutoPageSize=True)  # Enable pagination
            gb.configure_side_bar()  # Enable a sidebar for filtering
            gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)

            # Build grid options
            gridOptions = gb.build()

            # Display the grid
            AgGrid(individual_df, gridOptions=gridOptions)

            st.download_button(
                label="Export to Excel",
                data=convert_df(individual_df),
                file_name="individuals.xlsx",
                mime="application/vnd.ms-excel",
            )

@st.cache_data
def convert_df(df):
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

if __name__ == "__main__":
    main()