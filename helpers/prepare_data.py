"""
Script to prepare sample data for visualization.
Reads occurrence data and calculates species richness per grid cell,
then assigns colors based on a color ramp.
"""

import csv
import json
from collections import defaultdict

input_file = "../secret/HBF.113917-pentatomidae-suomi/occurrences.txt"
# Output file will be set based on resolution_km in main()


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


def convert_grid_cell_to_resolution(grid_cell, target_resolution_km):
    """
    Convert a grid cell coordinate to the specified resolution.
    
    Args:
        grid_cell (str): Grid cell in format "northing:easting" (e.g., "6789:3458")
        target_resolution_km (int): Target resolution in kilometers (1, 10, or 100)
    
    Returns:
        str: Grid cell in the target resolution format, or None if conversion fails
    """
    try:
        northing_str, easting_str = grid_cell.split(':')
        
        # Determine number of digits needed for target resolution
        if target_resolution_km == 1:
            digits_needed = 4
        elif target_resolution_km == 10:
            digits_needed = 3
        elif target_resolution_km == 100:
            digits_needed = 2
        else:
            print(f"Warning: Unsupported resolution {target_resolution_km}km. Use 1, 10, or 100.")
            return None
        
        # Convert to integers and truncate to desired number of digits
        # We do this by dividing by the appropriate power of 10 and truncating
        northing = int(northing_str)
        easting = int(easting_str)
        
        # Calculate divisor based on current number of digits and target
        # If input has more digits than needed, truncate from the right
        current_northing_digits = len(northing_str)
        current_easting_digits = len(easting_str)
        
        if current_northing_digits > digits_needed:
            divisor = 10 ** (current_northing_digits - digits_needed)
            northing = northing // divisor
        elif current_northing_digits < digits_needed:
            # Pad with zeros if input has fewer digits (shouldn't happen normally)
            northing = northing * (10 ** (digits_needed - current_northing_digits))
        
        if current_easting_digits > digits_needed:
            divisor = 10 ** (current_easting_digits - digits_needed)
            easting = easting // divisor
        elif current_easting_digits < digits_needed:
            # Pad with zeros if input has fewer digits (shouldn't happen normally)
            easting = easting * (10 ** (digits_needed - current_easting_digits))
        
        # Format with leading zeros if needed to match exact digit count
        return f"{northing:0{digits_needed}d}:{easting:0{digits_needed}d}"
    
    except (ValueError, AttributeError) as e:
        print(f"Warning: Invalid grid cell format '{grid_cell}': {e}")
        return None


def main():
    resolution_km = 1  # 1 | 10 | 100
    
    # Validate resolution
    if resolution_km not in [1, 10, 100]:
        print(f"Error: Invalid resolution {resolution_km}km. Must be 1, 10, or 100.")
        return
    
    # Set output file based on resolution
    output_file = f"../sampledata/celldata_pentatomidae_speciescount_{resolution_km}km.json"
    
    print(f"Processing data at {resolution_km}km resolution...")
    print(f"Output file: {output_file}")
    
    # Dictionary to store unique species per grid cell (at target resolution)
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
            
            # Convert grid cell to target resolution
            converted_grid_cell = convert_grid_cell_to_resolution(grid_cell, resolution_km)
            if converted_grid_cell is None:
                continue
            
            # Add species to the grid cell's set (automatically handles uniqueness)
            grid_cell_species[converted_grid_cell].add(scientific_name)
    
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
