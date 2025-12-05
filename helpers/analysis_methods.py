"""
Analysis methods for calculating species diversity metrics.
"""

import random
from collections import Counter

# Maximum total occurrences for a species to be considered "rare"
RARE_SPECIES_MAX_OCCURRENCES = 50


def calculate_speciescount(area_records):
    """
    Calculate species count (richness) for each grid cell.
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
                           Example: {"67:34": ["Species A", "Species B", "Species A"], ...}
    
    Returns:
        dict: Dictionary mapping grid cells to species counts
              Example: {"67:34": 2, "68:35": 5, ...}
    """
    result = {}
    for grid_cell, species_list in area_records.items():
        # Count unique species
        unique_species = set(species_list)
        result[grid_cell] = len(unique_species)
    
    return result


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


def calculate_incompleteness(area_species_list):
    """
    Calculate inventory incompleteness for an area using Chao1 estimator.
    
    Args:
        area_species_list (list): List of species names (with duplicates)
    
    Returns:
        float: Incompleteness ratio (0.0+), where 0.0 means fully sampled,
               higher values mean more species remain undiscovered
    """
    if not area_species_list:
        return 1.0
    
    # Count species occurrences
    species_counts = Counter(area_species_list)
    
    # Observed richness
    S_obs = len(species_counts)
    
    # Estimated richness using Chao1
    S_est = calculate_chao1_estimator(species_counts)
    
    if S_est == 0:
        return 1.0
    
    # Incompleteness = 1 - (Observed / Estimated)
    completeness = S_obs / S_est
    incompleteness = max(0.0, 1.0 - completeness)
    
    return incompleteness


def calculate_accumulation_slope(accumulation_curve):
    """
    Calculate the final slope of a species accumulation curve.
    This represents the rate of new species discovery per unit of effort.
    
    Args:
        accumulation_curve (list): Averaged species accumulation curve values
    
    Returns:
        float: Slope value (species per record)
    """
    if not accumulation_curve or len(accumulation_curve) < 2:
        return 0.0
    
    n_points = len(accumulation_curve)
    last_point = accumulation_curve[-1]
    
    # If fewer than 10 records, calculate slope over entire range
    if n_points < 10:
        first_point = accumulation_curve[0]
        if n_points == 1:
            return 0.0
        slope = (last_point - first_point) / (n_points - 1)
    else:
        # Calculate slope between last point and 10 records back
        point_10_back = accumulation_curve[n_points - 11]  # Index is n_points - 11 (0-indexed)
        slope = (last_point - point_10_back) / 10.0
    
    return slope


def calculate_chao1(area_records):
    """
    Calculate Chao1 incompleteness for each grid cell.
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
                           Example: {"67:34": ["Species A", "Species B", "Species A"], ...}
    
    Returns:
        dict: Dictionary mapping grid cells to incompleteness values (0.0 = fully sampled,
              higher = more species likely remain undiscovered)
              Example: {"67:34": 0.15, "68:35": 0.08, ...}
    """
    result = {}
    for grid_cell, species_list in area_records.items():
        incompleteness = calculate_incompleteness(species_list)
        result[grid_cell] = incompleteness
    
    return result


def calculate_accumulation_curve(area_records):
    """
    Calculate accumulation curve slope for each grid cell.
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
                           Example: {"67:34": ["Species A", "Species B", "Species A"], ...}
    
    Returns:
        dict: Dictionary mapping grid cells to slope values
              Example: {"67:34": 0.05, "68:35": 0.12, ...}
    """
    result = {}
    for grid_cell, species_list in area_records.items():
        # Build accumulation curve with 1000 iterations for rarefaction
        accumulation_curve = build_accumulation_curve(species_list, n_iterations=1000)
        
        # Calculate the final slope of the accumulation curve
        slope = calculate_accumulation_slope(accumulation_curve)
        result[grid_cell] = slope
    
    return result


def identify_rare_species(area_records, max_occurrences=RARE_SPECIES_MAX_OCCURRENCES):
    """
    Identify rare species based on total occurrences across all grid cells.
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
        max_occurrences (int): Maximum total occurrences for a species to be considered rare
                              (default: RARE_SPECIES_MAX_OCCURRENCES)
    
    Returns:
        set: Set of rare species names
    """
    total_counts = Counter()
    for species_list in area_records.values():
        total_counts.update(species_list)
    
    rare_species = {species for species, count in total_counts.items() 
                    if count <= max_occurrences}
    
    return rare_species


def find_indicator_species(area_records, rare_species):
    """
    Find indicator species that co-occur with rare species.
    
    An indicator species is a common species that appears in the same grid cell
    as a rare species. The co-occurrence count serves as a weight.
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
        rare_species (set): Set of rare species names
    
    Returns:
        dict: Dictionary mapping rare species to their indicator species with weights
              Example: {"Rare A": {"Common X": 2, "Common Y": 1}, ...}
    """
    indicators = {rs: Counter() for rs in rare_species}
    
    for species_list in area_records.values():
        unique_species = set(species_list)
        
        # For each rare species present in this cell
        for rs in rare_species:
            if rs in unique_species:
                # All other non-rare species in this cell are potential indicators
                for other_species in unique_species:
                    if other_species != rs and other_species not in rare_species:
                        indicators[rs][other_species] += 1
    
    # Filter out rare species with no indicators
    return {rs: counts for rs, counts in indicators.items() if counts}


def calculate_rare_species_potential(area_records):
    """
    Calculate rare species discovery potential for each grid cell.
    
    This method identifies areas with highest probability of having undiscovered
    populations of species that are very rare in the whole dataset. It works by:
    
    1. Identifying rare species (≤3 total occurrences across all cells)
    2. Finding "indicator species" - common species that co-occur with rare species
    3. Scoring cells based on presence of indicators but absence of rare species
    4. Weighting by cell incompleteness (poorly sampled cells score higher)
    
    Args:
        area_records (dict): Dictionary mapping grid cells to lists of species names
                           Example: {"67:34": ["Species A", "Species B", "Species A"], ...}
    
    Returns:
        dict: Dictionary mapping grid cells to potential scores (0.0-1.0)
              Higher scores indicate higher probability of undiscovered rare species
              Example: {"67:34": 0.75, "68:35": 0.23, ...}
    """
    if not area_records:
        return {}
    
    # Step 1: Identify rare species (≤RARE_SPECIES_MAX_OCCURRENCES total occurrences)
    rare_species = identify_rare_species(area_records)
    
    if not rare_species:
        # No rare species found, return zeros
        return {grid_cell: 0.0 for grid_cell in area_records}
    
    # Step 2: Find indicator species for each rare species
    indicators = find_indicator_species(area_records, rare_species)
    
    if not indicators:
        # No indicator relationships found
        return {grid_cell: 0.0 for grid_cell in area_records}
    
    # Step 3: Calculate potential score for each cell
    result = {}
    
    for grid_cell, species_list in area_records.items():
        unique_species = set(species_list)
        
        # Calculate incompleteness for this cell
        incompleteness = calculate_incompleteness(species_list)
        
        # Calculate indicator-based score
        cell_score = 0.0
        n_absent_rare = 0
        
        for rs, indicator_counts in indicators.items():
            # Only score for rare species that are ABSENT from this cell
            if rs not in unique_species:
                n_absent_rare += 1
                
                # Sum weights of indicator species that ARE present
                for indicator_sp, weight in indicator_counts.items():
                    if indicator_sp in unique_species:
                        cell_score += weight
        
        # Combine indicator score with incompleteness
        if n_absent_rare > 0 and cell_score > 0:
            # Normalize by number of absent rare species
            # Weight by incompleteness: poorly sampled cells have higher potential
            normalized_score = (cell_score / n_absent_rare) * (1 + incompleteness)
        else:
            normalized_score = 0.0
        
        result[grid_cell] = normalized_score
    
    # Normalize all scores to 0-1 range
    max_score = max(result.values()) if result else 0
    if max_score > 0:
        result = {cell: score / max_score for cell, score in result.items()}
    
    return result


# Method registry for easy lookup
METHODS = {
    "speciescount": calculate_speciescount,
    "chao1": calculate_chao1,
    "accumulation_curve": calculate_accumulation_curve,
    "rare_species_potential": calculate_rare_species_potential,
}


def get_method(method_name):
    """
    Get an analysis method by name.
    
    Args:
        method_name (str): Name of the method ("speciescount", "chao1", 
                          "accumulation_curve", or "rare_species_potential")
    
    Returns:
        callable: The analysis function
    
    Raises:
        ValueError: If method name is not recognized
    """
    if method_name not in METHODS:
        raise ValueError(
            f"Unknown method: {method_name}. "
            f"Available methods: {', '.join(METHODS.keys())}"
        )
    return METHODS[method_name]

