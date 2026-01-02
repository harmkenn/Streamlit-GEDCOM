import streamlit as st
import importlib.util
import os
import re

# Set the page layout to wide
st.set_page_config(layout="wide", page_title="Gedcoms")

def get_apps_from_folder(folder_path: str) -> dict:
    """
    Scans a folder for .py files and creates a dictionary mapping
    user-friendly names to their full file paths.
    """
    apps = {}
    if not os.path.isdir(folder_path):
        st.error(f"Error: App folder '{folder_path}' not found.")
        return apps

    for filename in os.listdir(folder_path):
        if filename.endswith('.py'):
            # Create a user-friendly name from the filename
            # e.g., 'FamilySearchTendril.py' becomes 'Family Search Tendril'
            base_name = os.path.splitext(filename)[0]
            friendly_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', base_name)
            
            app_path = os.path.join(folder_path, filename)
            apps[friendly_name] = app_path
            
    return apps

def run_app(app_path: str):
    """
    Dynamically imports and executes a Python module from a given path.
    """
    try:
        spec = importlib.util.spec_from_file_location(os.path.basename(app_path), app_path)
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
    except Exception as e:
        st.error(f"Error loading and running app '{os.path.basename(app_path)}': {e}")


# --- Main App Logic ---
APPS_FOLDER = 'apps'
available_apps = get_apps_from_folder(APPS_FOLDER)

if available_apps:
    st.sidebar.title("App Navigation")
    selected_app_name = st.sidebar.radio(
        'Select an app to run',
        list(available_apps.keys())
    )

    if selected_app_name:
        selected_app_path = available_apps[selected_app_name]
        run_app(selected_app_path)
else:
    st.warning("No applications found in the 'apps' folder.")

