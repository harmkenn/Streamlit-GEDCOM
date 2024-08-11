import pandas as pd
import streamlit as st
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")

def parse_gedcom(file_contents):
    # ... (rest of your code remains the same)

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
            st.dataframe(individual_df, use_container_width=True)

            # Store the DataFrame in session state
            st.session_state.individual_df = individual_df

            @st.cache_data
            def convert_df(df):
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                return excel_buffer

            excel_buffer = convert_df(individual_df)

            st.download_button(
                label="Export to Excel",
                data=excel_buffer,
                file_name="individuals.xlsx",
                mime="application/vnd.ms-excel",
            )

            # Create a GridOptionsBuilder object
            gb = GridOptionsBuilder.from_dataframe(individual_df)
            gb.configure_pagination(paginationAutoPageSize=True)  # Enable pagination
            gb.configure_side_bar()  # Enable a sidebar for filtering
            gb.configure_default_column(editable=True, groupable=True, sortable=True, filterable=True)

            # Build grid options
            gridOptions = gb.build()

            # Display the grid
            AgGrid(individual_df, gridOptions=gridOptions)

            # Add a button to apply filtering and sorting
            if st.button("Apply"):
                # Get the filtered data from the grid
                filtered_df = st.session_state.individual_df
                # Update the session state with the filtered data
                st.session_state.individual_df = filtered_df

if __name__ == "__main__":
    main()