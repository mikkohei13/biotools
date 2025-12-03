# Script to create map of Finland with some data

import json
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

finland_borders_file = "finland_borders.geojson"

squares_data = {"668:338": "#ff0000", "669:338": "#00ff00", "666:333": "#0000ff"}

# Read the GeoJSON file
with open(finland_borders_file, 'r') as f:
    geojson_data = json.load(f)

# Extract coordinates from the MultiPolygon
features = geojson_data['features']
if features:
    geometry = features[0]['geometry']
    if geometry['type'] == 'MultiPolygon':
        multipolygon = geometry['coordinates']
        
        # Create figure with white background
        fig, ax = plt.subplots(figsize=(12, 16), facecolor='white')
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
            northing_str, easting_str = square_key.split(':')
            northing = int(northing_str) * 10000
            easting = int(easting_str) * 10000
            
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
        
        # Save the figure
        output_file = "results/simplemap.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Map saved to {output_file}")
    else:
        print(f"Unexpected geometry type: {geometry['type']}")
else:
    print("No features found in GeoJSON")
