import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

# Get the current directory
current_directory = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the EdgeDriver executable located in the current directory
edge_driver_path = os.path.join(current_directory, 'msedgedriver')

# Setup Edge options
edge_options = Options()
edge_options.use_chromium = True

# Initialize EdgeDriver
service = Service(executable_path=edge_driver_path)
driver = webdriver.Edge(service=service, options=edge_options)

# Open a website
driver.get('https://familysearch.org')

# Perform your automated tasks here

# Close the browser
driver.quit()
