import streamlit as st
import gedcom
from gedcom.parser import Parser
from graphviz import Digraph

def parse_gedcom(file):
    # Initialize GEDCOM parser
    gedcom_parser = Parser()
    gedcom_parser.parse_file(file)

    # Extract individuals and relationships
    individuals = gedcom_parser.get_individuals()
    relationships = gedcom_parser.get_families()

    # Create a dictionary to store parsed data
    data = {
        "individuals": [],
        "relationships": []
    }

    # Parse individuals
    for individual in individuals:
        name = individual.get_name()
        birth_date = individual.get_birth_data()
        death_date = individual.get_death_data()
        data["individuals"].append({
            "id": individual.get_pointer(),
            "name": name,
            "birth_date": birth_date,
            "death_date": death_date
        })

    # Parse relationships
    for family in relationships:
        husband = family.get_husband()
        wife = family.get_wife()
        children = family.get_children()
        data["relationships"].append({
            "husband": husband.get_pointer() if husband else None,
            "wife": wife.get_pointer() if wife else None,
            "children": [child.get_pointer() for child in children]
        })

    return data

def visualize_family_tree(data):
    # Create a Graphviz Digraph for visualization
    dot = Digraph()

    # Add individuals as nodes
    for individual in data["individuals"]:
        dot.node(individual["id"], individual["name"])

    # Add relationships as edges
    for relationship in data["relationships"]:
        if relationship["husband"] and relationship["wife"]:
            dot.edge(relationship["husband"], relationship["wife"], label="Marriage")
        for child in relationship["children"]:
            if relationship["husband"]:
                dot.edge(relationship["husband"], child, label="Parent")
            if relationship["wife"]:
                dot.edge(relationship["wife"], child, label="Parent")

    return dot

# Streamlit app
def main():
    st.title("GEDCOM Family Tree Viewer")

    # File upload
    uploaded_file = st.file_uploader("Upload your GEDCOM file", type=["ged"])
    if uploaded_file:
        # Parse GEDCOM file
        data = parse_gedcom(uploaded_file)

        # Display parsed data
        st.subheader("Individuals")
        for individual in data["individuals"]:
            st.write(f"Name: {individual['name']}, Birth: {individual['birth_date']}, Death: {individual['death_date']}")

        st.subheader("Relationships")
        for relationship in data["relationships"]:
            st.write(f"Husband: {relationship['husband']}, Wife: {relationship['wife']}, Children: {relationship['children']}")

        # Visualize family tree
        st.subheader("Family Tree Visualization")
        dot = visualize_family_tree(data)
        st.graphviz_chart(dot)

if __name__ == "__main__":
    main()
