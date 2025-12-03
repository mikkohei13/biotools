"""
Test script to create a map from a JSON data file.
"""

import json
import os
import sys
from pathlib import Path
from helpers.simplemap import create_finland_map


data_directory = "sampledata"
data_filename = "celldata_pentatomidae_speciescount.json"
map_file_path = f"./results/{data_filename}_map.png"

data_file_path = f"{data_directory}/{data_filename}"

with open(data_file_path, 'r') as f:
    squares_data = json.load(f)

print(f"Creating map from {data_file_path}...")
success = create_finland_map(squares_data, map_file_path)
