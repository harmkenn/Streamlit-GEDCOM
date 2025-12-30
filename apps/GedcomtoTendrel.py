import streamlit as st
from io import StringIO
from datetime import datetime

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Descendant Filter Tool")

def parse_gedcom(file_contents):
    """
    Parses a GEDCOM file and extracts individuals and their relationships.
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

def find_descendants(individual_id, relationships, descendants=None):
    """
    Recursively finds all descendants of a given individual.
    """
    if descendants is None:
        descendants = []

    children = relationships["children"].get(individual_id, [])
    for child_id in children:
        if child_id not in descendants:
            descendants.append(child_id)
            find_descendants(child_id, relationships, descendants)

    return descendants

def filter_gedcom(individuals, relationships, ancestor_id):
    """
    Filters the GEDCOM to include only the ancestor, their descendants, and spouses.
    """
    descendants = find_descendants(ancestor_id, relationships)
    filtered_ids = set(descendants)
    filtered_ids.add(ancestor_id)  # Include the ancestor

    # Add spouses of descendants
    for descendant_id in descendants:
        spouses = relationships["spouses"].get(descendant_id, [])
        filtered_ids.update(spouses)

    # Build filtered GEDCOM
    filtered_gedcom = []
    for individual_id, individual_data in individuals.items():
        if individual_id in filtered_ids:
            filtered_gedcom.append(f"0 @{individual_id}@ INDI")
            for tag, values in individual_data.items():
                for value in values:
                    filtered_gedcom.append(f"1 {tag} {value}")
            # Add relationships
            for parent_id in relationships["parents"].get(individual_id, []):
                filtered_gedcom.append(f"1 FAMC @{parent_id}@")
            for spouse_id in relationships["spouses"].get(individual_id, []):
                filtered_gedcom.append(f"1 FAMS @{spouse_id}@")

    return "\n".join(filtered_gedcom)

def main():
    st.title("GEDCOM Descendant Filter Tool")
    st.sidebar.write("Upload a GEDCOM file and filter by ancestor")

    # File upload for GEDCOM
    gedcom_file = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if gedcom_file:
        try:
            # Read the uploaded file
            gedcom_contents = gedcom_file.read().decode('utf-8')

            # Parse the GEDCOM file
            individuals, relationships = parse_gedcom(gedcom_contents)

            # Select ancestor for filtering
            st.sidebar.subheader("Select Ancestor")
            ancestor_id = st.sidebar.selectbox(
                "Select an ancestor",
                options=list(individuals.keys()),
                format_func=lambda x: ' '.join(individuals[x].get('NAME', ['Unknown']))
            )

            if ancestor_id:
                # Filter GEDCOM
                filtered_gedcom = filter_gedcom(individuals, relationships, ancestor_id)

                # Display filtered GEDCOM
                st.subheader(f"Filtered GEDCOM for Ancestor: {' '.join(individuals[ancestor_id].get('NAME', ['Unknown']))}")
                st.text_area("Filtered GEDCOM", value=filtered_gedcom, height=400)

                # Download button for filtered GEDCOM
                st.download_button(
                    label="Download Filtered GEDCOM",
                    data=filtered_gedcom,
                    file_name="filtered_gedcom.ged",
                    mime="text/plain",
                )

        except Exception as e:
            st.error(f"Error processing GEDCOM file: {e}")

if __name__ == "__main__":
    main()
