import streamlit as st
import pandas as pd

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Individual Dataset Generator v1.4")

def parse_gedcom(file_contents):
    """
    Parses a GEDCOM file and extracts individuals and families.
    """
    individuals = {}
    families = {}
    current_individual = None
    current_family = None
    current_data = {}
    current_tag = None

    for line in file_contents.splitlines():
        line = line.strip()
        if line.startswith('0 @I'):  # Start of a new individual
            if current_individual is not None:
                individuals[current_individual] = current_data
                current_data = {}
            current_individual = line.split('@')[1]
        elif line.startswith('0 @F'):  # Start of a new family
            if current_family is not None:
                families[current_family] = current_data
                current_data = {}
            current_family = line.split('@')[1]
        elif line.startswith('1'):  # Level 1 tags
            parts = line.split(' ')
            current_tag = parts[1]
            value = parts[2:]
            current_data.setdefault(current_tag, []).append(' '.join(value))
        elif line.startswith('2'):  # Level 2 tags
            parts = line.split(' ')
            add_tag = parts[1]
            value = parts[2:]
            full_tag = current_tag + add_tag
            current_data.setdefault(full_tag, []).append(' '.join(value))
        else:
            continue

    if current_individual is not None:
        individuals[current_individual] = current_data
    if current_family is not None:
        families[current_family] = current_data

    return individuals, families

def generate_individual_dataset(individuals, families):
    """
    Generates a dataset of all individuals with the specified columns.
    """
    data = []

    for individual_id, individual_data in individuals.items():
        full_name = ' '.join(individual_data.get('NAME', ['Unknown']))
        gender = individual_data.get('SEX', ['Unknown'])[0]  # Extract gender
        birth_date = individual_data.get('BIRTDATE', ['Unknown'])[0]  # Extract birth date
        death_date = individual_data.get('DEATDATE', ['Unknown'])[0]  # Extract death date
        fams_ids = ', '.join(individual_data.get('FAMS', []))  # Spouse Family IDs
        famc_ids = ', '.join(individual_data.get('FAMC', []))  # Child Family IDs

        # Initialize parent information
        father_id = None
        father_name = None
        mother_id = None
        mother_name = None

        # Reverse lookup for parents using FAMC ID
        for famc_id in individual_data.get('FAMC', []):
            family = families.get(famc_id, {})
            father_id = family.get('HUSB', [None])[0]  # Father's ID
            mother_id = family.get('WIFE', [None])[0]  # Mother's ID
            if father_id:
                father_name = ' '.join(individuals.get(father_id, {}).get('NAME', ['Unknown']))
            if mother_id:
                mother_name = ' '.join(individuals.get(mother_id, {}).get('NAME', ['Unknown']))

        data.append({
            'ID Number': individual_id,
            'Full Name': full_name,
            'Gender': gender,  # Add gender column
            'Birth Date': birth_date,  # Add birth date column
            'Death Date': death_date,  # Add death date column
            'FAMS ID': fams_ids,
            'FAMC ID': famc_ids,
            "Father's ID Number": father_id,
            "Father's Full Name": father_name,
            "Mother's ID Number": mother_id,
            "Mother's Full Name": mother_name,
        })

    return pd.DataFrame(data)

def main():
    st.title("GEDCOM Individual Dataset Generator")
    st.sidebar.write("Upload a GEDCOM file to generate a dataset of individuals")

    # File upload for GEDCOM
    gedcom_file = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if gedcom_file:
        try:
            # Read the uploaded file
            gedcom_contents = gedcom_file.read().decode('utf-8')

            # Parse the GEDCOM file
            individuals, families = parse_gedcom(gedcom_contents)

            # Generate the dataset
            dataset = generate_individual_dataset(individuals, families)

            # Display the dataset
            st.subheader("Generated Dataset of Individuals")
            st.dataframe(dataset)

            # Download button for the dataset
            csv_data = dataset.to_csv(index=False)
            st.download_button(
                label="Download Dataset as CSV",
                data=csv_data,
                file_name="individual_dataset.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Error processing GEDCOM file: {e}")

if __name__ == "__main__":
    main()
