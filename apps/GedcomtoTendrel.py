import streamlit as st

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="GEDCOM Family Tree Tracer")

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

def trace_family_tree(start_family_id, families, individuals, traced_families=None):
    """
    Recursively traces the family tree starting from a specific family.
    """
    if traced_families is None:
        traced_families = []

    if start_family_id not in families:
        return traced_families

    # Add the current family to the traced families
    traced_families.append(start_family_id)

    # Get children of the current family
    children = families[start_family_id].get('CHIL', [])
    for child_id in children:
        # Find the families where the child is a parent (FAMS)
        child_families = individuals.get(child_id, {}).get('FAMS', [])
        for child_family_id in child_families:
            if child_family_id not in traced_families:
                trace_family_tree(child_family_id, families, individuals, traced_families)

    return traced_families

def filter_gedcom(traced_families, families, individuals):
    """
    Filters the GEDCOM to include only the traced families and their individuals.
    """
    filtered_gedcom = []

    # Add individuals linked to traced families
    for family_id in traced_families:
        if family_id in families:
            filtered_gedcom.append(f"0 @{family_id}@ FAM")
            for tag, values in families[family_id].items():
                for value in values:
                    filtered_gedcom.append(f"1 {tag} {value}")

            # Add individuals in the family
            parents = families[family_id].get('HUSB', []) + families[family_id].get('WIFE', [])
            children = families[family_id].get('CHIL', [])
            for individual_id in parents + children:
                if individual_id in individuals:
                    filtered_gedcom.append(f"0 @{individual_id}@ INDI")
                    for tag, values in individuals[individual_id].items():
                        for value in values:
                            filtered_gedcom.append(f"1 {tag} {value}")

    return "\n".join(filtered_gedcom)

def main():
    st.title("GEDCOM Family Tree Tracer")
    st.sidebar.write("Upload a GEDCOM file and trace a family tree")

    # File upload for GEDCOM
    gedcom_file = st.sidebar.file_uploader("Upload GEDCOM File", type=["ged"])

    if gedcom_file:
        try:
            # Read the uploaded file
            gedcom_contents = gedcom_file.read().decode('utf-8')

            # Parse the GEDCOM file
            individuals, families = parse_gedcom(gedcom_contents)

            # Select starting family for tracing
            st.sidebar.subheader("Select Starting Family")
            start_family_id = st.sidebar.selectbox(
                "Select a family",
                options=list(families.keys()),
                format_func=lambda x: f"Family {x} ({', '.join(families[x].get('HUSB', []) + families[x].get('WIFE', []))})"
            )

            if start_family_id:
                # Trace family tree
                traced_families = trace_family_tree(start_family_id, families, individuals)

                # Filter GEDCOM
                filtered_gedcom = filter_gedcom(traced_families, families, individuals)

                # Display traced family tree
                st.subheader(f"Traced Family Tree Starting from Family {start_family_id}")
                st.text_area("Filtered GEDCOM", value=filtered_gedcom, height=400)

                # Download button for filtered GEDCOM
                st.download_button(
                    label="Download Filtered GEDCOM",
                    data=filtered_gedcom,
                    file_name="filtered_family_tree.ged",
                    mime="text/plain",
                )

        except Exception as e:
            st.error(f"Error processing GEDCOM file: {e}")

if __name__ == "__main__":
    main()
