import streamlit as st
import pandas as pd

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Individual Dataset Generator v2.0")

def parse_gedcom(file_contents):
    """
    Parses a GEDCOM file and extracts individuals and families.
    Ensures clean separation between record types and avoids data bleed.
    """
    individuals = {}
    families = {}

    current_id = None
    current_type = None
    current_data = {}
    current_tag = None

    for raw_line in file_contents.splitlines():
        line = raw_line.strip()

        # Start of a new record
        if line.startswith("0 @"):
            # Save previous record
            if current_id and current_type == "INDI":
                individuals[current_id] = current_data
            elif current_id and current_type == "FAM":
                families[current_id] = current_data

            # Reset for new record
            parts = line.split(" ")
            current_id = parts[1].strip("@")
            current_type = parts[2] if len(parts) > 2 else None
            current_data = {}
            current_tag = None
            continue

        # Level 1 tag
        if line.startswith("1 "):
            parts = line.split(" ")
            current_tag = parts[1]
            value = " ".join(parts[2:])
            current_data.setdefault(current_tag, []).append(value)
            continue

        # Level 2 tag
        if line.startswith("2 "):
            parts = line.split(" ")
            sub_tag = parts[1]
            value = " ".join(parts[2:])
            full_tag = f"{current_tag}{sub_tag}"
            current_data.setdefault(full_tag, []).append(value)
            continue

    # Save last record
    if current_id and current_type == "INDI":
        individuals[current_id] = current_data
    elif current_id and current_type == "FAM":
        families[current_id] = current_data

    return individuals, families


def generate_individual_dataset(individuals, families):
    """
    Builds a clean dataset of individuals with parent lookup.
    """
    rows = []

    for ind_id, data in individuals.items():
        full_name = " ".join(data.get("NAME", ["Unknown"]))
        gender = data.get("SEX", ["Unknown"])[0]
        birth_date = data.get("BIRTDATE", ["Unknown"])[0]
        death_date = data.get("DEATDATE", ["Unknown"])[0]

        fams_ids = ", ".join(data.get("FAMS", []))
        famc_ids = ", ".join(data.get("FAMC", []))

        # Parent lookup
        father_id = mother_id = None
        father_name = mother_name = None

        for famc in data.get("FAMC", []):
            fam = families.get(famc, {})
            father_id = fam.get("HUSB", [None])[0]
            mother_id = fam.get("WIFE", [None])[0]

            if father_id:
                father_name = " ".join(individuals.get(father_id, {}).get("NAME", ["Unknown"]))
            if mother_id:
                mother_name = " ".join(individuals.get(mother_id, {}).get("NAME", ["Unknown"]))

        rows.append({
            "ID Number": ind_id,
            "Full Name": full_name,
            "Gender": gender,
            "Birth Date": birth_date,
            "Death Date": death_date,
            "FAMS ID": fams_ids,
            "FAMC ID": famc_ids,
            "Father's ID Number": father_id,
            "Father's Full Name": father_name,
            "Mother's ID Number": mother_id,
            "Mother's Full Name": mother_name,
        })

    return pd.DataFrame(rows)


def main():
    st.title("GEDCOM Individual Dataset Generator v2.0")
    st.sidebar.write("Upload a GEDCOM file to generate a dataset of individuals")

    uploaded = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if uploaded:
        try:
            contents = uploaded.read().decode("utf-8")

            individuals, families = parse_gedcom(contents)
            dataset = generate_individual_dataset(individuals, families)

            st.subheader("Generated Dataset of Individuals")
            st.dataframe(dataset, use_container_width=True)

            st.download_button(
                label="Download Dataset as CSV",
                data=dataset.to_csv(index=False),
                file_name="individual_dataset.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Error processing GEDCOM file: {e}")


if __name__ == "__main__":
    main()
