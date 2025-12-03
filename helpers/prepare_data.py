"""
Script to prepare sample data for visualization.
Reads occurrence data and calculates species richness per grid cell,
then assigns colors based on a color ramp.
"""

import csv
import json
from collections import defaultdict

input_file = "../secret/HBF.113917-pentatomidae-suomi/occurrences.txt"
output_file = "../sampledata/celldata_pentatomidae_speciescount.json"


def hex_color_ramp(value, min_val, max_val):
    """
    Generate a color from blue (low) to red (high) based on value.
    Returns a hex color string.
    """
    if max_val == min_val:
        return "#0000ff"  # Default to blue if all values are the same
    
    # Normalize value to 0-1 range
    normalized = (value - min_val) / (max_val - min_val)
    
    # Create color ramp: blue (low) -> cyan -> yellow -> red (high)
    if normalized < 0.33:
        # Blue to cyan
        r = 0
        g = int(255 * (normalized / 0.33))
        b = 255
    elif normalized < 0.67:
        # Cyan to yellow
        r = int(255 * ((normalized - 0.33) / 0.34))
        g = 255
        b = int(255 * (1 - (normalized - 0.33) / 0.34))
    else:
        # Yellow to red
        r = 255
        g = int(255 * (1 - (normalized - 0.67) / 0.33))
        b = 0
    
    return f"#{r:02x}{g:02x}{b:02x}"


def main():
    # Dictionary to store unique species per grid cell
    grid_cell_species = defaultdict(set)
    
    # Read the occurrences file
    # File has 3 header rows: DwC field names, Finnish names, English names
    # We use the first row (DwC) as column names and skip the next 2 rows
    with open(input_file, 'r', encoding='utf-8') as f:
        # Read first line (DwC field names) to get column names
        first_line = f.readline().strip()
        fieldnames = first_line.split('\t')
        
        # Skip the next 2 header rows (Finnish and English)
        f.readline()  # Skip Finnish header
        f.readline()  # Skip English header
        
        # Now create reader with the fieldnames we extracted
        reader = csv.DictReader(f, fieldnames=fieldnames, delimiter='\t')
        
        # Process each row
        for row in reader:
            grid_cell = row.get('gridCellYKJ', '').strip()
            scientific_name = row.get('scientificName', '').strip()
            
            # Skip rows without grid cell or scientific name
            if not grid_cell or not scientific_name:
                continue
            
            # Add species to the grid cell's set (automatically handles uniqueness)
            grid_cell_species[grid_cell].add(scientific_name)
    
    # Count species per grid cell and filter out zero-species cells
    species_counts = {
        grid_cell: len(species_set)
        for grid_cell, species_set in grid_cell_species.items()
        if len(species_set) > 0
    }
    
    if not species_counts:
        print("No valid grid cells with species found.")
        return
    
    # Find min and max species counts for color ramp
    min_count = min(species_counts.values())
    max_count = max(species_counts.values())
    
    print(f"Found {len(species_counts)} grid cells with species")
    print(f"Species count range: {min_count} - {max_count}")
    
    # Create output dictionary with colors
    output_data = {}
    for grid_cell, count in species_counts.items():
        color = hex_color_ramp(count, min_count, max_count)
        output_data[grid_cell] = color
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Output written to {output_file}")
    print(f"Sample of output: {dict(list(output_data.items())[:3])}")


if __name__ == "__main__":
    main()
