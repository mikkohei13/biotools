"""
Script to calculate species diversity completeness for each 100x100 km area.
Uses species accumulation curves and Chao1 estimator to determine how well
each area has been sampled.
"""

import csv
import json
import random
from collections import defaultdict, Counter


input_file = "../secret/HBF.113917-pentatomidae-suomi/occurrences.txt"
output_file = "../sampledata/celldata_pentatomidae_completeness_100km_colors.json"


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


def get_100km_grid_cell(grid_cell):
    """
    Convert a grid cell to 100km resolution by removing the last digit
    from both northing and easting.
    
    Args:
        grid_cell (str): Grid cell in format "northing:easting" (e.g., "678:345")
    
    Returns:
        str: Grid cell in 100km format (e.g., "67:34"), or None if conversion fails
    """
    try:
        northing_str, easting_str = grid_cell.split(':')
        
        # Remove last digit from both
        if len(northing_str) > 1:
            northing_100km = northing_str[:-1]
        else:
            return None  # Need at least 2 digits
        
        if len(easting_str) > 1:
            easting_100km = easting_str[:-1]
        else:
            return None  # Need at least 2 digits
        
        return f"{northing_100km}:{easting_100km}"
    
    except (ValueError, AttributeError) as e:
        return None


def build_accumulation_curve(species_list, n_iterations=1000):
    """
    Build a species accumulation curve by randomly shuffling records
    and tracking unique species found at each step.
    
    Args:
        species_list (list): List of species names (with duplicates representing abundance)
        n_iterations (int): Number of random permutations to average over
    
    Returns:
        list: Average number of unique species at each step
    """
    if not species_list:
        return []
    
    n_records = len(species_list)
    accumulation_curves = []
    
    for _ in range(n_iterations):
        # Shuffle the list randomly
        shuffled = species_list.copy()
        random.shuffle(shuffled)
        
        # Track unique species as we go through records
        seen_species = set()
        curve = []
        
        for species in shuffled:
            seen_species.add(species)
            curve.append(len(seen_species))
        
        accumulation_curves.append(curve)
    
    # Average across all iterations
    if not accumulation_curves:
        return []
    
    averaged_curve = []
    for i in range(n_records):
        step_values = [curve[i] for curve in accumulation_curves]
        averaged_curve.append(sum(step_values) / len(step_values))
    
    return averaged_curve


def calculate_chao1_estimator(species_counts):
    """
    Calculate Chao1 estimator for species richness.
    
    Chao1 = S_obs + (F1^2) / (2 * F2)
    where:
        S_obs = observed number of species
        F1 = number of singletons (species seen once)
        F2 = number of doubletons (species seen twice)
    
    Args:
        species_counts (dict or Counter): Dictionary mapping species to their counts
    
    Returns:
        float: Estimated total species richness
    """
    if not species_counts:
        return 0.0
    
    # Convert to Counter if needed
    if isinstance(species_counts, dict):
        counts = Counter(species_counts)
    else:
        counts = species_counts
    
    S_obs = len(counts)  # Observed species richness
    
    # Count singletons and doubletons
    F1 = sum(1 for count in counts.values() if count == 1)
    F2 = sum(1 for count in counts.values() if count == 2)
    
    # If F2 is 0, we can't use the standard formula
    # Use a simplified version or return observed
    if F2 == 0:
        # If there are singletons, estimate additional species
        # Using a conservative approach: add F1/2
        if F1 > 0:
            return S_obs + (F1 * (F1 - 1)) / 2.0
        else:
            return float(S_obs)
    
    # Standard Chao1 formula
    chao1 = S_obs + (F1 * F1) / (2.0 * F2)
    
    return chao1


def calculate_completeness(area_species_list):
    """
    Calculate inventory completeness for an area.
    
    Args:
        area_species_list (list): List of species names (with duplicates)
    
    Returns:
        float: Completeness ratio (0.0 to 1.0+), where 1.0 means fully sampled
    """
    if not area_species_list:
        return 0.0
    
    # Count species occurrences
    species_counts = Counter(area_species_list)
    
    # Observed richness
    S_obs = len(species_counts)
    
    # Estimated richness using Chao1
    S_est = calculate_chao1_estimator(species_counts)
    
    if S_est == 0:
        return 0.0
    
    # Completeness = Observed / Estimated
    completeness = S_obs / S_est
    
    # Cap at 1.0 (can't be more than 100% complete)
    # But also allow slightly above 1.0 if estimator underestimates
    return min(completeness, 1.5)  # Allow slight overestimation


def main():
    print("Calculating species diversity completeness for 100x100 km areas...")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Dictionary to store all records per 100km grid cell
    # Key: 100km grid cell, Value: list of species names (with duplicates)
    area_records = defaultdict(list)
    
    # Read the occurrences file
    # File has 3 header rows: DwC field names, Finnish names, English names
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
            
            # Convert to 100km grid cell
            area_100km = get_100km_grid_cell(grid_cell)
            if area_100km is None:
                continue
            
            # Add species record to this area
            area_records[area_100km].append(scientific_name)
    
    if not area_records:
        print("No valid records found.")
        return
    
    print(f"\nFound {len(area_records)} 100x100 km areas with records")
    
    # Calculate completeness for each area
    completeness_results = {}
    
    for area, species_list in area_records.items():
        # Calculate completeness using Chao1 estimator
        completeness = calculate_completeness(species_list)
        completeness_results[area] = completeness
        
        # Optional: Also build accumulation curve if needed for analysis
        # (not storing it in output to keep file size manageable)
    
    # Print statistics
    completeness_values = list(completeness_results.values())
    if completeness_values:
        print(f"\nCompleteness statistics:")
        print(f"  Mean: {sum(completeness_values) / len(completeness_values):.3f}")
        print(f"  Min: {min(completeness_values):.3f}")
        print(f"  Max: {max(completeness_values):.3f}")
        
        # Count areas by completeness category
        well_sampled = sum(1 for v in completeness_values if v >= 0.9)
        moderately_sampled = sum(1 for v in completeness_values if 0.5 <= v < 0.9)
        poorly_sampled = sum(1 for v in completeness_values if v < 0.5)
        
        print(f"\nSampling status:")
        print(f"  Well-sampled (≥0.9): {well_sampled} areas")
        print(f"  Moderately sampled (0.5-0.9): {moderately_sampled} areas")
        print(f"  Poorly sampled (<0.5): {poorly_sampled} areas")
    
    # Create output data with both color and value
    if completeness_values:
        min_completeness = min(completeness_values)
        max_completeness = max(completeness_values)
        
        completeness_data = {}
        for area, completeness in completeness_results.items():
            color = hex_color_ramp(completeness, min_completeness, max_completeness)
            completeness_data[area] = {
                "color": color,
                "value": completeness
            }
        
        # Write data with both color and value to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(completeness_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nOutput written to {output_file}")
        print(f"Sample of output: {dict(list(completeness_data.items())[:3])}")
    else:
        print("No completeness values to save.")


if __name__ == "__main__":
    main()

