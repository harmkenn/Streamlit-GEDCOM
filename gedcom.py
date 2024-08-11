import pandas as pd
import streamlit as st
from io import BytesIO
import openpyxl

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
    st.title("Gedcom to Excel")
    st.write("Upload a Gedcom file to parse its contents")

    uploaded_file = st.file_uploader("Choose a Gedcom file", type="ged")

    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode('utf-8')

    if st.button("Submit"):
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
            st.write(individual_df)

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

if __name__ == "__main__":
    main()