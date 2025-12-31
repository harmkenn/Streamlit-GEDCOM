import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Individual Dataset Generator v2.2")

# ---------------------------------------------------------
# GEDCOM PARSER (IMPROVED)
# ---------------------------------------------------------

def parse_gedcom(file_contents: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Parses GEDCOM file contents and extracts individuals and families.
    
    IMPROVEMENTS:
    - Handles multi-line continuation tags (CONC and CONT).
    - More robust parsing of lines to prevent data bleed.
    - Simplified logic for saving records.
    """
    individuals: Dict[str, Any] = {}
    families: Dict[str, Any] = {}
    current_id: Optional[str] = None
    current_type: Optional[str] = None
    records: Dict[str, Any] = {}
    last_tag_info: Dict[str, Any] = {}

    lines = file_contents.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(" ", 2)
        level = int(parts[0])
        
        if level == 0:
            # If we are at a new top-level record, save the previous one.
            if current_id and current_type:
                if current_type == "INDI":
                    individuals[current_id] = records
                elif current_type == "FAM":
                    families[current_id] = records

            # Start a new record
            if len(parts) > 2 and parts[2] in ("INDI", "FAM"):
                current_id = parts[1].strip("@")
                current_type = parts[2]
                records = {}
                last_tag_info = {}
            else: # Header or other non-individual/family record
                current_id = None
                current_type = None
        
        if not current_id:
            continue
            
        tag = parts[1].strip()
        value = parts[2] if len(parts) > 2 else ""

        if level == 1:
            if tag not in records:
                records[tag] = []
            records[tag].append(value)
            last_tag_info = {"tag": tag, "index": len(records[tag]) - 1}

        elif level > 1 and last_tag_info:
            # Handle continuation lines (CONC/CONT) for the last entry
            parent_tag = last_tag_info["tag"]
            parent_index = last_tag_info["index"]
            
            if tag == "CONC":
                records[parent_tag][parent_index] += value
            elif tag == "CONT":
                records[parent_tag][parent_index] += "\n" + value
            else: # Handle other sub-tags like '2 DATE', '2 PLAC'
                full_tag = f"{parent_tag}_{tag}"
                if full_tag not in records:
                    records[full_tag] = []
                records[full_tag].append(value)

    # Save the very last record in the file
    if current_id and current_type:
        if current_type == "INDI":
            individuals[current_id] = records
        elif current_type == "FAM":
            families[current_id] = records
            
    return individuals, families

# ---------------------------------------------------------
# DATASET GENERATOR (IMPROVED)
# ---------------------------------------------------------

def generate_individual_dataset(individuals: Dict[str, Any], families: Dict[str, Any]) -> pd.DataFrame:
    """
    Builds a clean dataset of individuals with corrected parent lookup.

    IMPROVEMENTS:
    - Fixes bug where only the last parent family record was used.
    - Uses helper function to avoid repetitive code for name lookup.
    - More resilient to missing data.
    """
    rows = []

    def get_person_name(ind_id: str) -> Optional[str]:
        if not ind_id:
            return None
        person_data = individuals.get(ind_id, {})
        # Replace slashes in name, common in GEDCOM format
        return person_data.get("NAME", [None])[0].replace("/", "")

    for ind_id, data in individuals.items():
        # FAMC can be a list; we only use the first one for parent lookup.
        famc_id = data.get("FAMC", [None])[0]

        father_id, mother_id = None, None
        if famc_id:
            family_data = families.get(famc_id, {})
            father_id = family_data.get("HUSB", [None])[0]
            mother_id = family_data.get("WIFE", [None])[0]

        rows.append({
            "ID Number": ind_id,
            "Full Name": get_person_name(ind_id),
            "Gender": data.get("SEX", [None])[0],
            "Birth Date": data.get("BIRT_DATE", [None])[0],
            "Death Date": data.get("DEAT_DATE", [None])[0],
            "FAMS ID": ", ".join(data.get("FAMS", [])),
            "FAMC ID": famc_id,
            "Father's ID Number": father_id,
            "Father's Full Name": get_person_name(father_id),
            "Mother's ID Number": mother_id,
            "Mother's Full Name": get_person_name(mother_id),
        })
    return pd.DataFrame(rows)

# ---------------------------------------------------------
# STREAMLIT APP (IMPROVED)
# ---------------------------------------------------------

def main():
    """Main function to run the Streamlit app."""
    st.title("GEDCOM Individual Dataset Generator v2.2")
    st.sidebar.header("Instructions")
    st.sidebar.write("Upload a GEDCOM file (.ged) to generate a dataset of individuals.")
    
    uploaded_file = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if uploaded_file:
        try:
            # Try decoding with utf-8, fall back to latin-1 for broader compatibility
            try:
                contents = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                contents = uploaded_file.read().decode("latin-1")
            
            with st.spinner("Parsing GEDCOM file..."):
                individuals, families = parse_gedcom(contents)
            
            if not individuals:
                st.warning("No individuals found in the uploaded GEDCOM file.")
                return

            with st.spinner("Generating dataset..."):
                dataset = generate_individual_dataset(individuals, families)

            st.subheader("Generated Dataset of Individuals")
            st.dataframe(dataset, use_container_width=True)

            csv_data = dataset.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Dataset as CSV",
                data=csv_data,
                file_name="individual_dataset.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            st.exception(e) # Provides a full traceback for debugging

if __name__ == "__main__":
    main()
