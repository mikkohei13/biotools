"""
This module creates a simple matplotlib map of Finland with data overlays.
It overlays colored squares representing data points on a 10km x 10km grid system.

The squares_data dictionary contains grid coordinates in the format "northing:easting"
where each coordinate unit represents 10km. For example, "668:338" represents
a square at northing 6,680,000 meters and easting 3,380,000 meters. Each square is rendered
as a 10 kilometers x 10 kilometers rectangle with the specified color.
"""

import json
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def create_finland_map(squares_data, output_file, borders_file=None, figsize=(12, 16), dpi=150):
    """
    Create a map of Finland with colored squares overlaid on a 10km x 10km grid.
    
    Args:
        squares_data (dict): Dictionary with grid coordinates as keys (format "northing:easting")
                           and hex color codes as values (e.g., {"668:338": "#ff0000"})
        output_file (str): Path to the output PNG file
        borders_file (str, optional): Path to the Finland borders GeoJSON file.
                                     Defaults to "finland_borders.geojson" in the same directory
                                     as this module.
        figsize (tuple, optional): Figure size in inches. Defaults to (12, 16).
        dpi (int, optional): Resolution in dots per inch. Defaults to 150.
    
    Returns:
        bool: True if the map was created successfully, False otherwise.
    """
    # Set default borders file path if not provided
    if borders_file is None:
        # Get the directory where this module is located
        module_dir = os.path.dirname(os.path.abspath(__file__))
        borders_file = os.path.join(module_dir, "finland_borders.geojson")
    
    # Read the GeoJSON file
    try:
        with open(borders_file, 'r') as f:
            geojson_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Borders file not found: {borders_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in borders file: {e}")
        return False
    
    # Extract coordinates from the MultiPolygon
    features = geojson_data.get('features', [])
    if not features:
        print("Error: No features found in GeoJSON")
        return False
    
    geometry = features[0].get('geometry', {})
    if geometry.get('type') != 'MultiPolygon':
        print(f"Error: Unexpected geometry type: {geometry.get('type')}")
        return False
    
    multipolygon = geometry['coordinates']
    
    # Create figure with white background
    fig, ax = plt.subplots(figsize=figsize, facecolor='white')
    ax.set_facecolor('white')
    
    # Plot each polygon in the MultiPolygon
    for polygon_group in multipolygon:
        for polygon in polygon_group:
            # Extract x and y coordinates
            coords = list(zip(*polygon))
            x_coords = coords[0]
            y_coords = coords[1]
            
            # Plot the polygon border
            ax.plot(x_coords, y_coords, 'k-', linewidth=0.5)
    
    # Add colored squares
    for square_key, color in squares_data.items():
        # Parse the key (e.g., "668:338")
        try:
            northing_str, easting_str = square_key.split(':')
            northing = int(northing_str) * 10000
            easting = int(easting_str) * 10000
        except ValueError:
            print(f"Warning: Invalid square key format: {square_key}. Expected 'northing:easting'")
            continue
        
        # Calculate square corners (10x10 km = 10000 meters)
        # Southwestern corner: (easting, northing)
        # Northeastern corner: (easting + 10000, northing + 10000)
        square = Rectangle(
            (easting, northing),  # bottom-left corner (x, y)
            10000,  # width
            10000,  # height
            facecolor=color,
            edgecolor='none'
        )
        ax.add_patch(square)
    
    # Remove axes for a clean look
    ax.axis('off')
    
    # Set equal aspect ratio and adjust limits
    ax.set_aspect('equal')
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Save the figure
    plt.tight_layout()
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)  # Close the figure to free memory
    
    print(f"Map saved to {output_file}")
    return True


# Allow running as a script for backward compatibility
if __name__ == "__main__":
    squares_data = {"668:338": "#ff0000", "669:338": "#00ff00", "666:333": "#0000ff"}
    output_file = "results/simplemap.png"
    create_finland_map(squares_data, output_file)
