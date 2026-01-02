import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import re

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Individual Dataset Generator v2.6")

# ---------------------------------------------------------
# GEDCOM PARSER (UNCHANGED)
# ---------------------------------------------------------

def parse_gedcom(file_contents: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Parses GEDCOM file contents and extracts individuals and families.
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
            if current_id and current_type:
                if current_type == "INDI":
                    individuals[current_id] = records
                elif current_type == "FAM":
                    families[current_id] = records

            if len(parts) > 2 and parts[2] in ("INDI", "FAM"):
                current_id = parts[1].strip("@")
                current_type = parts[2]
                records = {}
                last_tag_info = {}
            else:
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
            parent_tag = last_tag_info["tag"]
            parent_index = last_tag_info["index"]
            
            if tag == "CONC":
                records[parent_tag][parent_index] += value
            elif tag == "CONT":
                records[parent_tag][parent_index] += "\n" + value
            else:
                full_tag = f"{parent_tag}_{tag}"
                if full_tag not in records:
                    records[full_tag] = []
                records[full_tag].append(value)

    if current_id and current_type:
        if current_type == "INDI":
            individuals[current_id] = records
        elif current_type == "FAM":
            families[current_id] = records
            
    return individuals, families

# ---------------------------------------------------------
# HELPER FUNCTION FOR DATE FORMATTING (NEW)
# ---------------------------------------------------------

def format_gedcom_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parses various GEDCOM date formats into a single 'YYYY-MM-DD' format.
    Handles partial dates by padding with '01' for month/day.
    """
    if not date_str:
        return None

    # Clean the string from common GEDCOM keywords and ranges
    clean_date_str = re.sub(r'^(ABT|EST|CAL|INT|BEF|AFT|FROM|TO)\s+', '', date_str.strip(), flags=re.IGNORECASE)
    clean_date_str = re.sub(r'^BET\s+(.*?)\s+AND.*', r'\1', clean_date_str, flags=re.IGNORECASE)
    
    # Use pandas to_datetime which is powerful and can handle many formats.
    # errors='coerce' will turn unparseable dates into NaT (Not a Time).
    dt_object = pd.to_datetime(clean_date_str, errors='coerce')
    
    # If we have a valid datetime object, format it. Otherwise, return None.
    if pd.notna(dt_object):
        return dt_object.strftime('%Y-%m-%d')
    
    return None

# ---------------------------------------------------------
# DATASET GENERATOR (UPDATED)
# ---------------------------------------------------------

def generate_individual_dataset(individuals: Dict[str, Any], families: Dict[str, Any]) -> pd.DataFrame:
    """
    Builds a clean dataset of individuals with date formatting and parent lookup.
    """
    rows = []

    def get_person_name(ind_id: Optional[str]) -> Optional[str]:
        if not ind_id: return None
        person_data = individuals.get(ind_id, {})
        name = person_data.get("NAME", [None])[0]
        return name.replace("/", "") if isinstance(name, str) else None

    for ind_id, data in individuals.items():
        famc_id_raw = data.get("FAMC", [None])[0]
        famc_id = famc_id_raw.strip("@") if famc_id_raw else None

        father_id, mother_id = None, None
        if famc_id:
            family_data = families.get(famc_id, {})
            raw_father_id = family_data.get("HUSB", [None])[0]
            raw_mother_id = family_data.get("WIFE", [None])[0]
            father_id = raw_father_id.strip("@") if raw_father_id else None
            mother_id = raw_mother_id.strip("@") if raw_mother_id else None

        rows.append({
            "ID Number": ind_id,
            "Full Name": get_person_name(ind_id),
            "Gender": data.get("SEX", [None])[0],
            # --- DATE FORMATTING APPLIED HERE ---
            "Birth Date": format_gedcom_date(data.get("BIRT_DATE", [None])[0]),
            "Death Date": format_gedcom_date(data.get("DEAT_DATE", [None])[0]),
            "FAMS ID": ", ".join(id.strip("@") for id in data.get("FAMS", []) if id),
            "FAMC ID": famc_id,
            "Father's ID Number": father_id,
            "Father's Full Name": get_person_name(father_id),
            "Mother's ID Number": mother_id,
            "Mother's Full Name": get_person_name(mother_id),
        })
    return pd.DataFrame(rows)

# ---------------------------------------------------------
# DESCENDANT FINDER (UNCHANGED)
# ---------------------------------------------------------

def find_all_descendants(
    start_person_id: str,
    individuals: Dict[str, Any],
    families: Dict[str, Any],
    max_generations: int = 7
) -> set:
    """
    Finds all descendants of a given person up to a maximum number of generations.
    """
    if not start_person_id: return set()

    descendant_ids = set()
    queue = [(start_person_id, 1)]
    processed_ids = set()

    while queue:
        current_id, generation = queue.pop(0)

        if current_id in processed_ids: continue
        
        processed_ids.add(current_id)
        descendant_ids.add(current_id)

        if generation >= max_generations: continue

        person_data = individuals.get(current_id, {})
        fams_ids = person_data.get("FAMS", [])

        for fam_id in fams_ids:
            fam_id = fam_id.strip('@')
            if not fam_id: continue
            
            family_data = families.get(fam_id, {})

            husband_id = (family_data.get("HUSB", [None])[0] or "").strip('@')
            wife_id = (family_data.get("WIFE", [None])[0] or "").strip('@')

            if husband_id and husband_id != current_id: descendant_ids.add(husband_id)
            if wife_id and wife_id != current_id: descendant_ids.add(wife_id)

            children_ids = family_data.get("CHIL", [])
            for child_id in children_ids:
                child_id = child_id.strip('@')
                if child_id:
                    descendant_ids.add(child_id)
                    if child_id not in processed_ids:
                         queue.append((child_id, generation + 1))
    
    return descendant_ids

# ---------------------------------------------------------
# STREAMLIT APP (UNCHANGED)
# ---------------------------------------------------------

def main():
    """Main function to run the Streamlit app."""
    st.title("Ancestry.com GEDCOM Individual Dataset Generator v2.6")
    st.sidebar.header("Instructions")
    st.sidebar.write("Upload a GEDCOM file (.ged) to generate a dataset of individuals.")
    
    uploaded_file = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if uploaded_file:
        try:
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

            st.subheader("Generated Dataset of All Individuals")
            st.dataframe(dataset, use_container_width=True)

            csv_data = dataset.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Dataset as CSV",
                data=csv_data,
                file_name="individual_dataset.csv",
                mime="text/csv",
                key="download-full"
            )
            
            st.markdown("---")
            st.subheader("Descendant Analysis")
            
            name_list = dataset.dropna(subset=['Full Name']).apply(
                lambda row: f"{row['Full Name']} (ID: {row['ID Number']})", axis=1
            ).tolist()
            
            if not name_list:
                st.warning("No individuals with names found to select for descendant analysis.")
                return

            selected_person_str = st.selectbox(
                "Select an individual to find their descendants (up to 7 generations):",
                options=name_list
            )

            if selected_person_str:
                start_id = selected_person_str.split('(ID: ')[1].replace(')', '')
                
                with st.spinner(f"Finding descendants of {start_id}..."):
                    descendant_ids = find_all_descendants(
                        start_person_id=start_id,
                        individuals=individuals,
                        families=families,
                        max_generations=7
                    )
                
                if descendant_ids:
                    descendant_df = dataset[dataset['ID Number'].isin(descendant_ids)].copy()
                    
                    st.write(f"Found **{len(descendant_df)}** descendants (including spouses) for the selected individual.")
                    st.dataframe(descendant_df, use_container_width=True)

                    csv_desc_data = descendant_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Descendant Dataset as CSV",
                        data=csv_desc_data,
                        file_name=f"descendants_of_{start_id}.csv",
                        mime="text/csv",
                        key="download-desc"
                    )
                else:
                    st.info("No descendants found for the selected individual.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            st.exception(e)
main()
